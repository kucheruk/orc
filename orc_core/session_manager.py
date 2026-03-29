#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrates parallel agent sessions. Single session is the degenerate case."""

import asyncio
import logging
import threading
import time
import traceback
from argparse import Namespace
from pathlib import Path
from typing import Callable, Optional

from .backend import Backend, get_backend
from .integration_manager import IntegrationManager
from .logging import log_event
from .quit_signal import (
    is_quit_after_task_requested,
    is_session_stop_requested,
    is_stop_requested,
    request_session_stop,
    request_stop,
)
from .session_state import clear_active_session, save_active_session, save_worktree_record
from .session_types import (
    INTER_TASK_PAUSE_SECONDS,
    MANAGER_POLL_SECONDS,
    MAX_SESSIONS,
    RATE_LIMIT_MAX_RETRIES,
    SHUTDOWN_JOIN_TIMEOUT_SECONDS,
    STAGGER_DELAY_SECONDS,
    TRACEBACK_TRUNCATE,
    SessionSlot,
    SlotStatus,
    TaskContext,
    next_session_id,
)
from .state_paths import (
    metrics_path,
    parallel_runtime_path,
    parallel_task_path,
    run_root as state_run_root,
    stats_path,
)
from .stream_monitor_state import MonitorSnapshot, make_terminal_snapshot
from .task_distributor import TaskDistributor
from .task_execution import (
    SafeDict,
    TaskExecutionEngine,
    TaskExecutionRequest,
    TaskStageSpec,
    run_merge_expert_phase,
)
from .task_source import MarkdownTaskSource
from .task_state import delete_runtime_state_file
from .worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPT = 130
DROP_DEFAULT_SESSION = "s1"

SnapshotPublisher = Callable[[str, Optional[MonitorSnapshot]], None]

_logger = logging.getLogger(__name__)


class SessionManager:

    def __init__(
        self,
        *,
        workdir: str,
        backlog_path: Path,
        args: Namespace,
        log_path: Path,
        engine: TaskExecutionEngine,
        prompt_template: str,
        continue_template: str,
        commit_template: str,
        merge_expert_template: str = "",
        merge_expert_model: str = "",
        stage_specs: Optional[list[TaskStageSpec]] = None,
        integrate_to_main: bool = True,
        main_branch: str = "main",
        max_sessions: int = 1,
        task_source_factory: Callable[[Path], MarkdownTaskSource] = MarkdownTaskSource,
        sleep_fn: Callable[[float], None] = time.sleep,
        backend: Backend | None = None,
    ) -> None:
        self.backend: Backend = backend or get_backend()
        self.workdir = workdir
        self.backlog_path = backlog_path
        self.args = args
        self.log_path = log_path
        self.engine = engine
        self.prompt_template = prompt_template
        self.continue_template = continue_template
        self.commit_template = commit_template
        self.merge_expert_template = merge_expert_template
        self.merge_expert_model = (merge_expert_model or "").strip()
        self.stage_specs = tuple(stage_specs or ())
        self.integrate_to_main = bool(integrate_to_main)
        self.main_branch = (main_branch or "main").strip() or "main"
        self.max_sessions = max(1, min(max_sessions, MAX_SESSIONS))
        self.sleep_fn = sleep_fn

        mode = str(getattr(self.args, "mode", "backlog") or "backlog").strip().lower()

        self._slots: dict[str, SessionSlot] = {}
        self._slots_lock = threading.Lock()
        self._worktree_lock = threading.Lock()

        self._distributor = TaskDistributor(
            backlog_path=backlog_path,
            task_source_factory=task_source_factory,
            single_mode=(mode == "single"),
            selected_task_id=str(getattr(self.args, "task_id", "") or "").strip(),
            backend=self.backend,
        )
        backlog_relative = str(backlog_path.relative_to(Path(workdir).resolve()))
        self._integrator = IntegrationManager(
            workdir=workdir, main_branch=self.main_branch, log_path=log_path,
            safe_tracked_paths=frozenset({backlog_relative, f"{backlog_relative}.lock"}),
        )

        self.snapshot_publisher: Optional[SnapshotPublisher] = None
        self.task_body_publisher: Optional[Callable[[str, str], None]] = None
        self.session_removed_publisher: Optional[Callable[[str], None]] = None
        self.last_failure_reason = ""
        self._started_at = 0.0
        self._completed_tasks: list[str] = []
        self._failed_tasks: list[str] = []

    # ── Public API (TUI thread) ──────────────────────────────────

    def request_add_session(self) -> Optional[str]:
        return self._start_session()

    def request_remove_session(self, session_id: str = "") -> None:
        with self._slots_lock:
            slot = self._find_slot_to_close(session_id)
            if slot:
                slot.status = SlotStatus.CLOSING
        if slot:
            request_session_stop(slot.session_id)
            log_event(self.log_path, "INFO", "session closing", session_id=slot.session_id)

    # ── Main entry ───────────────────────────────────────────────

    def run(self, snapshot_publisher: SnapshotPublisher) -> int:
        self.snapshot_publisher = snapshot_publisher
        self._started_at = time.time()
        self._broadcast_status("Recovering git state...")
        self._integrator.recover_stale_git_state()
        self._handle_drop()
        self._broadcast_status("Installing hooks...")
        self._ensure_hooks()

        open_task_count = self._distributor.open_task_count()
        effective_sessions = min(self.max_sessions, open_task_count)

        self._broadcast_status(f"Starting session 1/{effective_sessions}...")
        first_sid = self._start_session()
        if not first_sid:
            return EXIT_OK

        if effective_sessions > 1:
            self._broadcast_status("Analyzing task conflicts...")
            self._run_analysis()
            self._launch_remaining_sessions(effective_sessions)

        try:
            return self._manager_loop()
        except KeyboardInterrupt:
            raise
        finally:
            self._shutdown_all()

    def _broadcast_status(self, message: str) -> None:
        if self.task_body_publisher:
            try:
                self.task_body_publisher("_global", f"[bold yellow]{message}[/bold yellow]")
            except Exception:
                pass

    def _launch_remaining_sessions(self, effective_sessions: int) -> None:
        for i in range(1, effective_sessions):
            if is_stop_requested():
                break
            self._broadcast_status(f"Starting session {i + 1}/{effective_sessions}...")
            self._start_session()
            if i < effective_sessions - 1:
                self.sleep_fn(STAGGER_DELAY_SECONDS)

    async def run_async(self, snapshot_publisher: SnapshotPublisher) -> int:
        return await asyncio.to_thread(self.run, snapshot_publisher)

    def shutdown(self) -> None:
        self._shutdown_all()

    def get_summary(self) -> str:
        elapsed = time.time() - self._started_at if self._started_at > 0 else 0
        mins, secs = divmod(int(elapsed), 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
        done, _ip, total = self._distributor.get_progress()
        lines = [
            f"Completed: {len(self._completed_tasks)} tasks in {time_str}",
        ]
        if self._completed_tasks:
            lines.append(f"  Tasks: {', '.join(self._completed_tasks)}")
        if self._failed_tasks:
            lines.append(f"  Failed: {', '.join(self._failed_tasks)}")
        lines.append(f"  Backlog: {done}/{total} done")
        return "\n".join(lines)

    # ── Manager loop ─────────────────────────────────────────────

    def _manager_loop(self) -> int:
        while True:
            self._reap_finished_slots()

            if is_stop_requested():
                return EXIT_INTERRUPT

            if not self._has_active_slots():
                return self._on_all_sessions_done()

            self.sleep_fn(MANAGER_POLL_SECONDS)

    def _on_all_sessions_done(self) -> int:
        with self._slots_lock:
            failed = [s for s in self._slots.values() if s.error]
        if failed:
            self.last_failure_reason = failed[0].error
            return EXIT_FAILURE

        if self.max_sessions > 1 and self._distributor.has_remaining_tasks():
            self._run_analysis()
            self._restart_idle_slots()
            if self._has_active_slots():
                return self._manager_loop()

        return EXIT_OK

    def _has_active_slots(self) -> bool:
        with self._slots_lock:
            return any(s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
                       for s in self._slots.values())

    # ── Session lifecycle ────────────────────────────────────────

    def _start_session(self) -> Optional[str]:
        with self._slots_lock:
            active = sum(1 for s in self._slots.values()
                         if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING, SlotStatus.CLOSING))
            if active >= self.max_sessions:
                return None
            sid = next_session_id()
            slot = SessionSlot(session_id=sid)
            self._slots[sid] = slot

        self._launch_slot_thread(slot)
        self._notify_session_added(sid)
        log_event(self.log_path, "INFO", "session started", session_id=sid)
        return sid

    def _launch_slot_thread(self, slot: SessionSlot) -> None:
        thread = threading.Thread(
            target=self._run_session, args=(slot,),
            daemon=True, name=f"orc-session-{slot.session_id}")
        with self._slots_lock:
            slot.thread = thread
            slot.status = SlotStatus.RUNNING
        thread.start()

    def _notify_session_added(self, sid: str) -> None:
        if not self.snapshot_publisher:
            return
        try:
            self.snapshot_publisher(sid, None)
        except Exception as exc:
            _logger.debug("snapshot_publisher failed for session %s: %s", sid, exc)

    def _notify_task_body(self, session_id: str, body: str) -> None:
        if not self.task_body_publisher:
            return
        try:
            self.task_body_publisher(session_id, body)
        except Exception as exc:
            _logger.debug("task_body_publisher failed: %s", exc)

    # ── Session thread ───────────────────────────────────────────

    def _run_session(self, slot: SessionSlot) -> None:
        session_id = slot.session_id
        rate_limit_retries = 0
        try:
            while self._should_continue(slot):
                task = self._distributor.pick_next_task(session_id)
                if task is None:
                    break
                ok, was_rate_limited = self._process_one_task(slot, task, rate_limit_retries)
                if was_rate_limited:
                    rate_limit_retries += 1
                    continue
                if not ok:
                    break
                rate_limit_retries = 0
                if self._should_stop_after_task():
                    break
                self.sleep_fn(INTER_TASK_PAUSE_SECONDS)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.error = f"session_crashed:{type(exc).__name__}"
            log_event(self.log_path, "ERROR", "session crashed",
                      session_id=session_id, error=str(exc),
                      traceback=traceback.format_exc()[:TRACEBACK_TRUNCATE])
            task_id = slot.task.task_id if slot.task else session_id
            self._publish_terminal_snapshot(
                session_id, task_id,
                phase="failed", status=slot.error,
                base=slot.last_snapshot,
            )
        else:
            # Normal exit: no more tasks or stop requested
            if not slot.error:
                task_id = slot.task.task_id if slot.task else session_id
                self._publish_terminal_snapshot(
                    session_id, task_id,
                    phase="completed", status="all tasks done",
                    base=slot.last_snapshot,
                )
                self.sleep_fn(10.0)
                self._publish_session_removed(session_id)
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    def _should_continue(self, slot: SessionSlot) -> bool:
        return (not is_stop_requested()
                and not is_session_stop_requested(slot.session_id)
                and slot.status != SlotStatus.CLOSING)

    def _should_stop_after_task(self) -> bool:
        if is_quit_after_task_requested():
            return True
        return self._distributor.is_single_mode

    def _process_one_task(self, slot, task, rate_limit_retries) -> tuple[bool, bool]:
        """Returns (success, was_rate_limited)."""
        slot.task = task
        self._notify_task_body(slot.session_id, task.text)
        worktree = self._create_worktree(slot, task)
        slot.worktree = worktree
        if worktree is None and self.max_sessions > 1:
            log_event(self.log_path, "ERROR",
                      "skipping task: worktree required in multi-session mode",
                      session_id=slot.session_id, task_id=task.task_id)
            return (False, False)
        ctx = TaskContext(slot=slot, task=task, worktree=worktree)
        effective_workdir = ctx.workdir or self.workdir
        self._ensure_hooks_for_workspace(effective_workdir)

        result = self._execute_task(ctx, effective_workdir)

        if result is None or result.status == "failed":
            if self._is_rate_limited(slot) and rate_limit_retries < RATE_LIMIT_MAX_RETRIES:
                self._backoff_after_rate_limit(ctx, rate_limit_retries)
                return (True, True)
            self._record_failure(ctx, result)
            return (False, False)

        if result.delay_seconds > 0:
            self.sleep_fn(result.delay_seconds)

        if result.status == "completed":
            if not self._finalize_completed_task(ctx, effective_workdir):
                return (False, False)
            self._broadcast_progress_update()

        return (True, False)

    # ── Rate limiting ────────────────────────────────────────────

    def _is_rate_limited(self, slot: SessionSlot) -> bool:
        return (slot.last_snapshot is not None
                and slot.last_snapshot.live_phase == "network_problem")

    def _backoff_after_rate_limit(self, ctx: TaskContext, retries: int) -> None:
        backoff = _rate_limit_backoff(retries + 1)
        log_event(self.log_path, "WARN", "rate limit detected, backing off",
                  session_id=ctx.session_id, task_id=ctx.task_id,
                  backoff_seconds=backoff, attempt=retries + 1)
        self._distributor.release_task(ctx.task_id)
        self._cleanup_worktree_silent(ctx.worktree)
        ctx.slot.worktree = None
        self.sleep_fn(backoff)

    # ── Task failure / completion ────────────────────────────────

    def _record_failure(self, ctx: TaskContext, result) -> None:
        reason = (result.reason if result else "execution_crashed") or "unknown"
        ctx.slot.error = reason
        self._failed_tasks.append(ctx.task_id)
        log_event(self.log_path, "ERROR", "task failed",
                  session_id=ctx.session_id, task_id=ctx.task_id, reason=reason)
        self._publish_terminal_snapshot(
            ctx.session_id, ctx.task_id, phase="failed", status=reason,
            base=ctx.slot.last_snapshot,
        )
        if self.max_sessions == 1:
            self.last_failure_reason = reason
            save_active_session(self.workdir, {
                "version": 1, "task_id": ctx.task_id,
                "task_file": str(parallel_task_path(self.workdir, ctx.session_id)),
                "worktree_path": ctx.workdir,
                "status": "failed", "reason": reason,
            })

    def _publish_terminal_snapshot(
        self,
        session_id: str,
        task_id: str,
        *,
        phase: str,
        status: str,
        base: Optional[MonitorSnapshot] = None,
    ) -> None:
        snapshot = make_terminal_snapshot(task_id, phase, status, base=base)
        with self._slots_lock:
            slot = self._slots.get(session_id)
            if slot is not None:
                slot.last_snapshot = snapshot
        if self.snapshot_publisher:
            try:
                self.snapshot_publisher(session_id, snapshot)
            except Exception:
                pass

    def _broadcast_progress_update(self) -> None:
        """Push updated done/in_progress/total to all active session snapshots."""
        from dataclasses import replace
        done, in_progress, total = self._distributor.get_progress()
        # Collect updates under lock, publish outside to avoid deadlock
        pending: list[tuple[str, MonitorSnapshot]] = []
        with self._slots_lock:
            for sid, slot in self._slots.items():
                if slot.last_snapshot is not None and slot.status == SlotStatus.RUNNING:
                    updated = replace(
                        slot.last_snapshot,
                        progress_done=done,
                        progress_total=total,
                        progress_in_progress=in_progress,
                    )
                    slot.last_snapshot = updated
                    pending.append((sid, updated))
        if self.snapshot_publisher:
            for sid, snapshot in pending:
                try:
                    self.snapshot_publisher(sid, snapshot)
                except Exception:
                    pass

    def _publish_session_removed(self, session_id: str) -> None:
        if self.session_removed_publisher:
            try:
                self.session_removed_publisher(session_id)
            except Exception:
                pass

    def _finalize_completed_task(self, ctx: TaskContext, effective_workdir: str) -> bool:
        if self.integrate_to_main:
            def _status(msg: str) -> None:
                self._notify_task_body(ctx.session_id, f"[bold]{msg}[/bold]")

            merge_fn = self._make_merge_fn(ctx)
            try:
                ok = self._integrator.integrate(
                    ctx.slot, ctx.task, effective_workdir, merge_fn, status_fn=_status)
            except Exception as exc:
                # Integration crashed — ensure worktree is cleaned up
                log_event(self.log_path, "ERROR", "integration crashed",
                          session_id=ctx.session_id, task_id=ctx.task_id, error=str(exc))
                ok = False
            if ok:
                _status(f"INTEGRATED {ctx.task_id} into {self.main_branch}")
            else:
                _status(f"INTEGRATION FAILED for {ctx.task_id} — work preserved on branch, continuing")
                log_event(
                    self.log_path, "WARN",
                    "integration failed, skipping task and continuing session",
                    session_id=ctx.session_id, task_id=ctx.task_id,
                )
                self._publish_terminal_snapshot(
                    ctx.session_id, ctx.task_id, phase="failed",
                    status="integration_failed (branch preserved)", base=ctx.slot.last_snapshot,
                )
                # Don't kill the session — clean up worktree with force and move on.
                # Keep task in _assigned_ids so no other session re-does the work.
                self._cleanup_worktree_silent(ctx.worktree)
                ctx.slot.worktree = None
                self._failed_tasks.append(ctx.task_id)
                if self.max_sessions == 1:
                    self.last_failure_reason = "main_integration_failed"
                    return False
                return True

        if not self._cleanup_worktree_checked(ctx):
            return False

        clear_active_session(self.workdir)
        # Mark completed in distributor — keeps task in _assigned_ids AND adds
        # to _completed_ids so progress counters are accurate even when base
        # BACKLOG.md still shows [ ] (cherry-pick went to master, not working copy).
        self._distributor.mark_completed(ctx.task_id)
        self._completed_tasks.append(ctx.task_id)
        return True

    def _make_merge_fn(self, ctx: TaskContext) -> Callable[[], bool]:
        def merge_expert() -> bool:
            return self._run_merge_expert(ctx.slot, ctx.task)
        return merge_expert

    # ── Task execution ───────────────────────────────────────────

    def _execute_task(self, ctx: TaskContext, effective_workdir: str):
        request = self._build_request(ctx, effective_workdir)
        try:
            return self.engine.execute(request)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log_event(self.log_path, "ERROR", "engine.execute crashed",
                      session_id=ctx.session_id, task_id=ctx.task_id, error=str(exc))
            return None

    def _build_request(self, ctx: TaskContext, effective_workdir: str) -> TaskExecutionRequest:
        session_id = ctx.session_id
        task_path = parallel_task_path(self.workdir, session_id)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        done, in_progress, total = self._distributor.get_progress()

        return TaskExecutionRequest(
            task=ctx.task,
            backlog_path=self.backlog_path,
            backlog_arg=self.args.backlog,
            task_path=task_path,
            workdir=effective_workdir,
            base_workdir=self.workdir,
            run_root=state_run_root(self.workdir, f"session-{session_id}"),
            model=self.args.model,
            commit_model=self._resolve_model(self.args.commit_model),
            merge_expert_model=self.merge_expert_model or self._resolve_model(self.args.commit_model),
            prompt_template=self.prompt_template,
            continue_template=self.continue_template,
            commit_template=self.commit_template,
            merge_expert_template=self.merge_expert_template,
            commit_phase=bool(self.args.commit_phase) and not bool(self.stage_specs),
            integrate_to_main=False,
            main_branch=self.main_branch,
            allow_fallback_commits=bool(getattr(self.args, "allow_fallback_commits", False)),
            enforce_stage_artifacts=bool(getattr(self.args, "require_stage_artifacts", False)),
            stage_specs=self.stage_specs,
            progress_done=done,
            progress_total=total,
            progress_in_progress=in_progress,
            agent_env=self._build_agent_env(session_id, task_path),
            agent_output_log_path=self._agent_output_log_path(),
            snapshot_publisher=self._make_slot_publisher(session_id),
            **self._timing_args(),
        )

    def _timing_args(self) -> dict:
        return {
            "poll": self.args.poll,
            "stall_timeout": self.args.stall_timeout,
            "task_ttl": self.args.task_ttl,
            "max_restarts": self.args.max_restarts,
            "report_interval": self.args.report_interval,
            "summary_lines": self.args.summary_lines,
            "nudge_after": self.args.nudge_after,
            "nudge_cooldown": self.args.nudge_cooldown,
            "nudge_text": self.args.nudge_text,
            "commit_stall_timeout": self.args.commit_stall_timeout,
            "commit_ttl": self.args.commit_ttl,
        }

    def _agent_output_log_path(self) -> Optional[str]:
        raw = str(getattr(self.args, "agent_output_log_path", "") or "").strip()
        return raw or None

    def _resolve_model(self, candidate) -> str:
        return (str(candidate or "").strip()) or self.args.model

    def _build_agent_env(self, session_id: str, task_path: Path) -> dict[str, str]:
        return {
            "ORC_TASK_FILE": str(task_path),
            "ORC_TASK_RUNTIME_FILE": str(parallel_runtime_path(self.workdir, session_id)),
            "ORC_BASE_WORKSPACE": str(self.workdir),
            "ORC_SESSION_ID": session_id,
            "ORC_STATS_FILE": str(stats_path(self.workdir)),
            "ORC_METRICS_FILE": str(metrics_path(self.workdir)),
        }

    # ── Merge expert ─────────────────────────────────────────────

    def _run_merge_expert(self, slot: SessionSlot, task) -> bool:
        ctx = TaskContext(slot=slot, task=task)
        request = self._build_request(ctx, self.workdir)
        tag = f"{ctx.session_id}__{ctx.task_id}"
        return run_merge_expert_phase(
            worker=self.engine.worker, request=request,
            prompt_vars=SafeDict(
                task_text=task.text, task_id=ctx.task_id,
                backlog=self.args.backlog, workspace=self.workdir),
            task_id=ctx.task_id, tag=tag, log_path=self.log_path,
            agent_output_log_path=str(
                getattr(self.args, "agent_output_log_path", "") or "").strip() or None,
            timeline_id=tag, attempt=0,
        )

    # ── Worktree ─────────────────────────────────────────────────

    def _create_worktree(self, slot: SessionSlot, task) -> Optional[WorktreeSession]:
        with self._worktree_lock:
            try:
                wt = create_task_worktree(
                    base_workdir=self.workdir, task_id=task.task_id,
                    log_path=self.log_path, main_branch=self.main_branch)
                save_worktree_record(self.workdir, task.task_id, {
                    "version": 1, "task_id": task.task_id,
                    "worktree_path": wt.worktree_path,
                    "branch_name": wt.branch_name, "base_workdir": self.workdir,
                })
                return wt
            except Exception as exc:
                log_event(self.log_path, "ERROR", "worktree creation failed",
                          session_id=slot.session_id, task_id=task.task_id, error=str(exc))
                return None

    def _cleanup_worktree_checked(self, ctx: TaskContext) -> bool:
        if not ctx.worktree:
            return True
        with self._worktree_lock:
            try:
                cleanup_task_worktree(ctx.worktree, self.log_path)
                ctx.slot.worktree = None
                return True
            except Exception as exc:
                ctx.slot.error = f"worktree_cleanup_failed:{type(exc).__name__}"
                log_event(self.log_path, "ERROR", "worktree cleanup failed",
                          session_id=ctx.session_id, task_id=ctx.task_id, error=str(exc))
                if self.max_sessions == 1:
                    self.last_failure_reason = ctx.slot.error
                return False

    def _cleanup_worktree_silent(self, worktree: Optional[WorktreeSession]) -> None:
        if not worktree:
            return
        # Serialize worktree operations to avoid races with concurrent integration
        with self._worktree_lock:
            try:
                cleanup_task_worktree(worktree, self.log_path)
            except Exception:
                # Force-remove if normal cleanup fails (e.g. worktree has uncommitted changes)
                try:
                    from .worktree_flow import run_git
                    run_git(worktree.base_workdir, ["git", "worktree", "remove", "--force", worktree.worktree_path])
                    run_git(worktree.base_workdir, ["git", "worktree", "prune"])
                except Exception as exc2:
                    _logger.debug("worktree force cleanup failed: %s", exc2)

    # ── Analysis ─────────────────────────────────────────────────

    def _run_analysis(self) -> None:
        with self._slots_lock:
            existing = [s.session_id for s in self._slots.values()]
        self._distributor.run_analysis(
            workdir=self.workdir, model=self.args.model, log_path=self.log_path,
            max_sessions=self.max_sessions, existing_session_ids=existing,
        )

    # ── Hooks ────────────────────────────────────────────────────

    @property
    def _hooks_enabled(self) -> bool:
        return bool(getattr(self.args, "hooks", False))

    def _ensure_hooks(self) -> None:
        if not self._hooks_enabled:
            return
        self.backend.setup_hooks(self.workdir, self.log_path)

    def _ensure_hooks_for_workspace(self, workdir: str) -> None:
        if not self._hooks_enabled:
            return
        if not workdir or workdir == self.workdir:
            return
        self.backend.setup_hooks(workdir, self.log_path)

    # ── Drop ─────────────────────────────────────────────────────

    def _handle_drop(self) -> None:
        if not bool(self.args.drop):
            return
        task_path = parallel_task_path(self.workdir, DROP_DEFAULT_SESSION)
        if not task_path.exists():
            return
        try:
            task_path.unlink()
            delete_runtime_state_file(task_path, self.log_path, reason="drop_active_task_state")
            log_event(self.log_path, "WARN", "drop: active task state deleted")
        except Exception as exc:
            log_event(self.log_path, "ERROR", "drop: failed", error=str(exc))

    # ── Snapshot publisher ───────────────────────────────────────

    def _make_slot_publisher(self, session_id: str) -> Callable[[MonitorSnapshot], None]:
        def publish(snapshot: MonitorSnapshot) -> None:
            slot = self._slots.get(session_id)
            if slot is not None:
                slot.last_snapshot = snapshot
            if self.snapshot_publisher:
                self.snapshot_publisher(session_id, snapshot)
        return publish

    # ── Slot utilities ───────────────────────────────────────────

    def _find_slot_to_close(self, session_id: str) -> Optional[SessionSlot]:
        if session_id and session_id in self._slots:
            slot = self._slots[session_id]
            return slot if slot.status == SlotStatus.RUNNING else None
        running = [s for s in self._slots.values() if s.status == SlotStatus.RUNNING]
        return running[-1] if running else None

    def _reap_finished_slots(self) -> None:
        with self._slots_lock:
            for slot in self._slots.values():
                if slot.status == SlotStatus.CLOSED and slot.thread and not slot.thread.is_alive():
                    slot.thread = None

    def _restart_idle_slots(self) -> None:
        with self._slots_lock:
            closed_ok = [s for s in self._slots.values()
                         if s.status == SlotStatus.CLOSED and not s.error]
        for slot in closed_ok:
            if self._distributor.has_queued_tasks(slot.session_id):
                with self._slots_lock:
                    slot.error = ""
                self._launch_slot_thread(slot)

    # ── Shutdown ─────────────────────────────────────────────────

    def _shutdown_all(self) -> None:
        request_stop()
        with self._slots_lock:
            threads = [s.thread for s in self._slots.values()
                       if s.thread and s.thread.is_alive()]
        for thread in threads:
            thread.join(timeout=SHUTDOWN_JOIN_TIMEOUT_SECONDS)


def _rate_limit_backoff(attempt: int) -> float:
    from .session_types import RATE_LIMIT_BASE_BACKOFF_SECONDS, RATE_LIMIT_MAX_BACKOFF_SECONDS
    return float(min(
        RATE_LIMIT_BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)),
        RATE_LIMIT_MAX_BACKOFF_SECONDS,
    ))
