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

from .hooks import ensure_repo_hooks, ensure_repo_hooks_config
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
from .stream_monitor_state import MonitorSnapshot
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
    ) -> None:
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
        )
        self._integrator = IntegrationManager(
            workdir=workdir, main_branch=self.main_branch, log_path=log_path,
        )

        self.snapshot_publisher: Optional[SnapshotPublisher] = None
        self.last_failure_reason = ""

    # ── Public API (TUI thread) ──────────────────────────────────

    def request_add_session(self) -> None:
        self._start_session()

    def request_remove_session(self, session_id: str = "") -> None:
        with self._slots_lock:
            slot = self._find_slot_to_close(session_id)
        if slot:
            slot.status = SlotStatus.CLOSING
            request_session_stop(slot.session_id)
            log_event(self.log_path, "INFO", "session closing", session_id=slot.session_id)

    # ── Main entry ───────────────────────────────────────────────

    def run(self, snapshot_publisher: SnapshotPublisher) -> int:
        self.snapshot_publisher = snapshot_publisher
        self._integrator.recover_stale_git_state()
        self._handle_drop()
        self._ensure_hooks()

        if self.max_sessions > 1:
            self._run_analysis()

        if not self._launch_initial_sessions():
            return EXIT_OK

        try:
            return self._manager_loop()
        except KeyboardInterrupt:
            raise
        finally:
            self._shutdown_all()

    async def run_async(self, snapshot_publisher: SnapshotPublisher) -> int:
        return await asyncio.to_thread(self.run, snapshot_publisher)

    def shutdown(self) -> None:
        self._shutdown_all()

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

    def _launch_initial_sessions(self) -> bool:
        for i in range(self.max_sessions):
            if not self._start_session():
                break
            if i < self.max_sessions - 1 and self.max_sessions > 1:
                self.sleep_fn(STAGGER_DELAY_SECONDS)
                if is_stop_requested():
                    break
        return self._has_active_slots()

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
        worktree = self._create_worktree(slot, task)
        slot.worktree = worktree
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
        log_event(self.log_path, "ERROR", "task failed",
                  session_id=ctx.session_id, task_id=ctx.task_id, reason=reason)
        if self.max_sessions == 1:
            self.last_failure_reason = reason
            save_active_session(self.workdir, {
                "version": 1, "task_id": ctx.task_id,
                "task_file": str(parallel_task_path(self.workdir, ctx.session_id)),
                "worktree_path": ctx.workdir,
                "status": "failed", "reason": reason,
            })

    def _finalize_completed_task(self, ctx: TaskContext, effective_workdir: str) -> bool:
        if self.integrate_to_main:
            merge_fn = self._make_merge_fn(ctx)
            if not self._integrator.integrate(ctx.slot, ctx.task, effective_workdir, merge_fn):
                ctx.slot.error = "integration_failed"
                if self.max_sessions == 1:
                    self.last_failure_reason = "main_integration_failed"
                return False

        if not self._cleanup_worktree_checked(ctx):
            return False

        clear_active_session(self.workdir)
        self._distributor.release_task(ctx.task_id)
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
        done, total = self._distributor.get_progress()

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
        try:
            cleanup_task_worktree(worktree, self.log_path)
        except Exception as exc:
            _logger.debug("worktree cleanup (silent) failed: %s", exc)

    # ── Analysis ─────────────────────────────────────────────────

    def _run_analysis(self) -> None:
        with self._slots_lock:
            existing = [s.session_id for s in self._slots.values()]
        self._distributor.run_analysis(
            workdir=self.workdir, model=self.args.model, log_path=self.log_path,
            max_sessions=self.max_sessions, existing_session_ids=existing,
        )

    # ── Hooks ────────────────────────────────────────────────────

    def _ensure_hooks(self) -> None:
        before_path, stop_path = ensure_repo_hooks(self.workdir)
        ensure_repo_hooks_config(self.workdir, before_path, stop_path, self.log_path)

    def _ensure_hooks_for_workspace(self, workdir: str) -> None:
        if not workdir or workdir == self.workdir:
            return
        before_path, stop_path = ensure_repo_hooks(workdir)
        ensure_repo_hooks_config(workdir, before_path, stop_path, self.log_path)

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
                self._launch_slot_thread(slot)
                slot.error = ""

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
