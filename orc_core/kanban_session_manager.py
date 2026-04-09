#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban-mode session manager: teamlead + workers with pull-based role dispatch."""

from __future__ import annotations

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
from .kanban_agent_output import process_agent_result
from .kanban_card import KanbanCard, new_card_body
from .kanban_distributor import KanbanDistributor
from .kanban_constants import Action
from .kanban_pull import ROLE_INTEGRATOR, WorkAssignment
from .kanban_publisher import KanbanPublisher
from .kanban_request_builder import build_kanban_request
from .notify import send_telegram_message
from .kanban_roles import ROLE_TEAMLEAD, build_prompt, build_teamlead_prompt
from .teamlead_incident import (
    DECISION_FILENAME,
    FIX_CARD_PREFIX,
    INCIDENT_FIX_TIMEOUT,
    SCALE_DOWN_WAIT_TIMEOUT,
    Incident,
    IncidentPhase,
    build_incident_prompt,
    fallback_decision,
    parse_incident_decision,
)
from .logging import log_event
from .quit_signal import is_quit_after_task_requested, is_session_stop_requested, is_stop_requested
from .session_types import (
    MANAGER_POLL_SECONDS,
    MAX_SESSIONS,
    SHUTDOWN_JOIN_TIMEOUT_SECONDS,
    STAGGER_DELAY_SECONDS,
    SessionSlot,
    SlotStatus,
    next_session_id,
)
from .stream_monitor_state import MonitorSnapshot
from .task_execution import TaskExecutionEngine
from .task_source import Task
from .worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPT = 130


def _teamlead_decision_path(workdir: str) -> Path:
    """Return the standard teamlead decision file path."""
    p = Path(workdir) / ".orc"
    p.mkdir(parents=True, exist_ok=True)
    return p / "teamlead-decision.md"

SnapshotPublisher = Callable[[str, Optional[MonitorSnapshot]], None]
_logger = logging.getLogger(__name__)


class KanbanSessionManager:
    """Orchestrates AI agents on a kanban board using a pull system."""

    def __init__(
        self,
        *,
        workdir: str,
        tasks_dir: Path,
        args: Namespace,
        log_path: Path,
        engine: TaskExecutionEngine,
        commit_template: str = "",
        merge_expert_template: str = "",
        merge_expert_model: str = "",
        main_branch: str = "main",
        max_sessions: int = 4,
        backend: Backend | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.backend: Backend = backend or get_backend()
        self.workdir = workdir
        self.tasks_dir = tasks_dir
        self.args = args
        self.log_path = log_path
        self.engine = engine
        self.commit_template = commit_template
        self.merge_expert_template = merge_expert_template
        self.merge_expert_model = (merge_expert_model or "").strip()
        self.main_branch = (main_branch or "main").strip() or "main"
        self.max_sessions = max(2, min(max_sessions, MAX_SESSIONS))
        self.sleep_fn = sleep_fn

        self._distributor = KanbanDistributor(tasks_dir)
        self._integrator = IntegrationManager(
            workdir=workdir, main_branch=self.main_branch, log_path=log_path,
            safe_tracked_paths=frozenset(),
        )
        self._slots: dict[str, SessionSlot] = {}
        self._slots_lock = threading.Lock()
        self._worktree_lock = threading.Lock()

        self.snapshot_publisher: Optional[SnapshotPublisher] = None
        self.publisher = KanbanPublisher()
        self._session_snapshots: dict[str, MonitorSnapshot] = {}
        self.last_failure_reason = ""
        self._started_at = 0.0
        self._completed_tasks: list[str] = []
        self._failed_tasks: list[str] = []
        self._handled_crash_slots: set[str] = set()
        self._incident_counter: int = 0
        self._card_fail_counts: dict[str, int] = {}  # card_id → consecutive failures
        self._arbitrated_at_loop: dict[str, int] = {}  # card_id → loop_count at last arbitration
        self._directive_queue: list[str] = []
        self._directive_lock = threading.Lock()
        self._last_health_check: float = 0.0

    # ── Public API ──────────────────────────────────────────────

    def request_add_session(self) -> Optional[str]:
        return self._start_session(role="worker")

    def request_remove_session(self, session_id: str = "") -> None:
        with self._slots_lock:
            candidates = [s for s in self._slots.values()
                          if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)]
            if session_id:
                slot = next((s for s in candidates if s.session_id == session_id), None)
            else:
                slot = candidates[-1] if candidates else None
        if slot:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSING
            log_event(self.log_path, "INFO", "session closing", session_id=slot.session_id)

    def run(self, snapshot_publisher: SnapshotPublisher) -> int:
        self.snapshot_publisher = snapshot_publisher
        self._started_at = time.time()
        self.publisher.set_started_at(self._started_at)
        self._wire_board_callbacks()
        self._distributor.refresh()
        self._release_stale_agents()
        done, _ip, total = self._distributor.get_progress()
        self.publisher._emit("system", "", f"Kanban started: {total} cards, {self.max_sessions} agents")
        self._publish_board_state()
        self._integrator.recover_stale_git_state()
        self._start_session(role=ROLE_TEAMLEAD)
        self._publish_board_state()
        self.sleep_fn(STAGGER_DELAY_SECONDS)
        for _ in range(self.max_sessions - 1):
            if is_stop_requested():
                break
            self._start_session(role="worker")
            self.sleep_fn(STAGGER_DELAY_SECONDS)
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

    def get_summary(self) -> str:
        elapsed = time.time() - self._started_at if self._started_at > 0 else 0
        mins, secs = divmod(int(elapsed), 60)
        hours, mins = divmod(mins, 60)
        time_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
        done, _ip, total = self._distributor.get_progress()
        lines = [f"Completed: {len(self._completed_tasks)} tasks in {time_str}"]
        if self._completed_tasks:
            lines.append(f"  Tasks: {', '.join(self._completed_tasks)}")
        if self._failed_tasks:
            lines.append(f"  Failed: {', '.join(self._failed_tasks)}")
        lines.append(f"  Board: {done}/{total} done")
        return "\n".join(lines)

    def _wire_board_callbacks(self) -> None:
        board = self._distributor.board
        board.on_move = lambda cid, frm, to, reason: self.publisher.log_move(cid, frm, to, reason)
        board.on_action_change = lambda cid, old, new, role: self.publisher.log_action_change(cid, old, new, role)

    def _release_stale_agents(self) -> None:
        """Release cards stuck with assigned_agent from a crashed previous run."""
        board = self._distributor.board
        released = 0
        done_ids: set[str] = set()
        for card in list(board.cards):
            if card.stage == "8_Done":
                done_ids.add(card.id)
            if card.assigned_agent and card.stage != "8_Done":
                old_agent = card.assigned_agent
                board.release_agent(card)
                released += 1
                self.publisher._emit(
                    "system", card.id,
                    f"{card.id} released stale agent {old_agent}",
                )
                log_event(self.log_path, "INFO", "released stale agent",
                          task_id=card.id, old_agent=old_agent)
        if released:
            self.publisher._emit("system", "", f"Released {released} stale agent(s) from previous run")
        # Cleanup worktrees for cards that are Done
        self._cleanup_done_worktrees(done_ids)

    def _cleanup_done_worktrees(self, done_ids: set[str]) -> None:
        """Remove worktrees for cards that reached Done."""
        from .worktree_flow import _safe_name
        from .state_paths import worktrees_root
        wt_root = worktrees_root(self.workdir)
        if not wt_root.exists():
            return
        cleaned = 0
        for card_id in done_ids:
            safe = _safe_name(card_id)
            wt_path = wt_root / safe
            if wt_path.exists():
                from .worktree_flow import cleanup_task_worktree, WorktreeSession
                session = WorktreeSession(
                    base_workdir=self.workdir,
                    worktree_path=str(wt_path),
                    branch_name=f"orc/{safe}",
                    task_id=card_id,
                )
                try:
                    cleanup_task_worktree(session, self.log_path)
                    cleaned += 1
                except Exception as exc:
                    log_event(self.log_path, "WARN", "failed to cleanup done worktree",
                              task_id=card_id, error=str(exc)[:200])
        if cleaned:
            self.publisher._emit("system", "", f"Cleaned {cleaned} worktree(s) from completed cards")

    # ── Manager loop ─────────────────────────────────────────────

    def _manager_loop(self) -> int:
        quit_after_logged = False
        quit_after_last_status = 0.0
        while True:
            self._reap_finished_slots()
            self._publish_board_state()
            if is_stop_requested():
                return EXIT_INTERRUPT
            if is_quit_after_task_requested():
                if not quit_after_logged:
                    self.publisher._emit("system", "", "Quit-after-task: waiting for active agents to finish...")
                    quit_after_logged = True
                running = self._running_slots_info()
                now = time.time()
                if running:
                    if now - quit_after_last_status >= 10.0:
                        self.publisher._emit("system", "", f"Still working: {running}")
                        quit_after_last_status = now
                else:
                    self.publisher._emit("system", "", "All agents finished, exiting")
                    return EXIT_OK
            elif not self._has_active_slots():
                if self._distributor.has_remaining_work():
                    self._restart_idle_slots()
                    if self._has_active_slots():
                        continue
                return EXIT_OK
            self.sleep_fn(MANAGER_POLL_SECONDS)

    def _running_slots_info(self) -> str:
        with self._slots_lock:
            running = [s for s in self._slots.values() if s.status == SlotStatus.RUNNING and s.thread and s.thread.is_alive()]
        if not running:
            return ""
        # Show actual assignment status — only report active card if slot has a task
        parts = []
        for s in running:
            if s.task:
                parts.append(f"{s.session_id}({s.task.text})")
            else:
                parts.append(f"{s.session_id}(idle)")
        return ", ".join(parts)

    def _publish_board_state(self) -> None:
        self._distributor.refresh()
        self.publisher.publish_board(self._distributor.board, self._session_snapshots)

    def _has_active_slots(self) -> bool:
        with self._slots_lock:
            return any(s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
                       for s in self._slots.values())

    def _reap_finished_slots(self) -> None:
        with self._slots_lock:
            for slot in self._slots.values():
                if slot.thread and not slot.thread.is_alive() and slot.status == SlotStatus.RUNNING:
                    slot.status = SlotStatus.CLOSED
                    slot.thread = None

    def _restart_idle_slots(self) -> None:
        with self._slots_lock:
            closed = [s for s in self._slots.values() if s.status == SlotStatus.CLOSED]
        for slot in closed:
            self._launch_slot_thread(slot)

    # ── Session lifecycle ────────────────────────────────────────

    def _start_session(self, role: str = "worker") -> Optional[str]:
        with self._slots_lock:
            active = sum(1 for s in self._slots.values()
                         if s.status in (SlotStatus.IDLE, SlotStatus.RUNNING, SlotStatus.CLOSING))
            if active >= self.max_sessions:
                self.publisher._emit("system", "", f"Cannot add agent: {active}/{self.max_sessions} slots used")
                return None
            sid = next_session_id()
            slot = SessionSlot(session_id=sid)
            self._slots[sid] = slot
        slot.role = role
        self._launch_slot_thread(slot)
        self.publisher._emit("system", "", f"{sid} session created (role={role})")
        if self.snapshot_publisher:
            self.snapshot_publisher(sid, None)
        log_event(self.log_path, "INFO", "kanban session started", session_id=sid, role=role)
        return sid

    def _launch_slot_thread(self, slot: SessionSlot) -> None:
        role = slot.role or "worker"
        target = self._run_teamlead if role == ROLE_TEAMLEAD else self._run_worker
        thread = threading.Thread(target=target, args=(slot,), daemon=True,
                                  name=f"kanban-{slot.session_id}")
        with self._slots_lock:
            slot.thread = thread
            slot.status = SlotStatus.RUNNING
        thread.start()

    # ── Worker thread ────────────────────────────────────────────

    def _run_worker(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self.publisher._emit("system", "", f"{sid} worker started, scanning board...")
        try:
            idle_reason_logged: str = ""
            while self._should_continue(slot):
                self._distributor.refresh()
                assignment = self._distributor.pick_worker_task(sid)
                if assignment is None:
                    reason = self._distributor.diagnose_no_work()
                    if reason != idle_reason_logged:
                        self.publisher._emit("system", "", f"{sid} idle — {reason}")
                        idle_reason_logged = reason
                    self.sleep_fn(2.0)
                    if not self._distributor.has_remaining_work():
                        self.publisher._emit("system", "", f"{sid} no remaining work, stopping")
                        break
                    continue
                idle_reason_logged = ""
                self._execute_assignment(slot, assignment)
                if is_quit_after_task_requested():
                    self.publisher._emit("system", "", f"{sid} finished task, exiting (quit-after-task)")
                    break
                self.sleep_fn(1.0)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.crash_traceback = traceback.format_exc()[:2000]
            slot.error = f"worker_crashed:{type(exc).__name__}"
            self.publisher._emit("escalate", "", f"{sid} CRASHED: {type(exc).__name__}: {exc}")
            log_event(self.log_path, "ERROR", "worker crashed",
                      session_id=sid, error=str(exc),
                      traceback=traceback.format_exc()[:2000])
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    def _execute_assignment(self, slot: SessionSlot, assignment: WorkAssignment) -> None:
        card, role, sid = assignment.card, assignment.role, slot.session_id
        self.publisher.log_assign(card.id, role, sid)
        log_event(self.log_path, "INFO", "executing",
                  session_id=sid, task_id=card.id, role=role, stage=card.stage)
        prompt = build_prompt(role, card, self._distributor.board)
        task_start = time.time()
        worktree: Optional[WorktreeSession] = None
        try:
            if assignment.needs_worktree:
                with self._worktree_lock:
                    worktree = create_task_worktree(
                        base_workdir=self.workdir, task_id=card.id,
                        log_path=self.log_path, main_branch=self.main_branch,
                    )
                wd = worktree.worktree_path
                if not worktree.reused:
                    self.publisher._emit("system", card.id, f"{card.id} worktree ready")
            else:
                wd = self.workdir
            task = Task(task_id=card.id, text=card.title or card.id, done=False)
            slot.task = task
            self.publisher._emit("system", card.id, f"{card.id} launching {role} agent...")
            result = self.engine.execute(self._make_request(task, prompt, wd, sid,
                                                            assignment.needs_worktree, 1800.0))
            if result and result.status == "completed":
                elapsed = time.time() - task_start
                old_stage = card.stage
                old_action = card.action
                old_cos = card.class_of_service
                errors = process_agent_result(self._distributor.board, card, role)
                if not errors:
                    self._completed_tasks.append(card.id)
                    self.publisher.log_complete(card.id, role, elapsed)
                    self._notify_completion(card, role, old_stage, old_action, old_cos, elapsed)
                else:
                    self.publisher._emit("escalate", card.id,
                                         f"{card.id} validation failed: {'; '.join(errors[:3])}")
                    log_event(self.log_path, "WARN", "agent output validation failed",
                              task_id=card.id, role=role, errors=str(errors))
                    self._failed_tasks.append(card.id)
            else:
                reason = result.reason if result else "no result"
                self.publisher._emit("escalate", card.id, f"{card.id} {role} failed: {reason}")
                self._failed_tasks.append(card.id)
        except Exception as exc:
            self.publisher._emit("escalate", card.id,
                                 f"{card.id} ERROR: {type(exc).__name__}: {exc}")
            log_event(self.log_path, "ERROR", "assignment failed",
                      task_id=card.id, error=str(exc))
            self._failed_tasks.append(card.id)
            # Track consecutive failures — deterministic errors will repeat forever
            count = self._card_fail_counts.get(card.id, 0) + 1
            self._card_fail_counts[card.id] = count
            if count >= 2:
                try:
                    card.action = Action.BLOCKED.value
                    self._distributor.board.save_card(card)
                    self.publisher._emit("escalate", card.id,
                                         f"{card.id} marked Blocked after {count} consecutive failures: {exc}")
                    log_event(self.log_path, "WARN", "card blocked after repeated failures",
                              task_id=card.id, fail_count=count, error=str(exc))
                    send_telegram_message(
                        f"🚫 {card.id} заблокирована после {count} подряд ошибок: {type(exc).__name__}: {exc}",
                        log_path=self.log_path,
                    )
                except Exception:
                    pass
        else:
            # Reset failure counter on success
            self._card_fail_counts.pop(card.id, None)
        finally:
            slot.task = None  # clear so _running_slots_info shows idle, not stale task
            self._distributor.release_card(card.id)
            # Only cleanup worktree when card reaches Done — reuse for loop-backs
            if worktree and card.stage == "8_Done":
                with self._worktree_lock:
                    cleanup_task_worktree(worktree, self.log_path)

    # ── Teamlead thread ──────────────────────────────────────────

    _HEALTH_CHECK_INTERVAL = 60.0  # seconds between proactive health checks

    def _run_teamlead(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self.publisher._emit("system", "", f"{sid} teamlead started, monitoring board...")
        incident: Optional[Incident] = None
        try:
            while self._should_continue(slot):
                self._distributor.refresh()
                if incident is not None:
                    # ── Incident mode: process state machine ──
                    incident = self._process_incident(slot, incident)
                    if incident is None:
                        self.publisher._emit("incident", "",
                                             "Incident resolved, resuming normal operations")
                    self.sleep_fn(2.0)
                    if is_quit_after_task_requested():
                        self.publisher._emit("system", "", f"{sid} teamlead exiting (quit-after-task)")
                        break
                    continue

                # ── Priority 1: user directives ──
                directive = self._pop_directive()
                if directive:
                    self._teamlead_directive(slot, sid, directive)
                    continue

                # ── Priority 2: anomaly detection (worker crashes) ──
                anomaly = self._detect_anomaly()
                if anomaly is not None:
                    incident = anomaly
                    self.publisher.log_incident(
                        incident.id,
                        f"{incident.error_type} on {incident.source_task_id or incident.source_slot_id}: "
                        f"{incident.error_message[:200]}",
                    )
                    log_event(self.log_path, "WARN", "incident detected",
                              incident_id=incident.id, error_type=incident.error_type,
                              source_task=incident.source_task_id, source_slot=incident.source_slot_id)
                    continue

                # ── Priority 3: board health check (periodic, only when problems found) ──
                if time.time() - self._last_health_check >= self._HEALTH_CHECK_INTERVAL:
                    if self._teamlead_health_check(slot, sid):
                        continue

                # ── Priority 4: card arbitration (looping / blocked cards) ──
                self._teamlead_arbitrate(slot, sid)

                if not self._distributor.has_remaining_work():
                    self.publisher._emit("system", "", f"{sid} teamlead: no remaining work")
                    break
                self.sleep_fn(5.0)
                if is_quit_after_task_requested():
                    self.publisher._emit("system", "", f"{sid} teamlead exiting (quit-after-task)")
                    break
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.error = f"teamlead_crashed:{type(exc).__name__}"
            log_event(self.log_path, "ERROR", "teamlead crashed",
                      session_id=sid, error=str(exc),
                      traceback=traceback.format_exc()[:2000])
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    # ── Teamlead: card-level arbitration ───────────────────────────

    def _find_latest_agent_log(self, card_id: str) -> str:
        """Find the most recent raw-stream log for a card across all kanban sessions."""
        from .state_paths import run_root
        runs_dir = run_root(self.workdir, "").parent / "runs"
        if not runs_dir.exists():
            return ""
        best: Path | None = None
        for session_dir in runs_dir.iterdir():
            if not session_dir.name.startswith("kanban-"):
                continue
            stream_dir = session_dir / "raw-stream"
            if not stream_dir.is_dir():
                continue
            for log_file in stream_dir.glob(f"*__{card_id}.log"):
                if best is None or log_file.stat().st_mtime > best.stat().st_mtime:
                    best = log_file
        return str(best) if best else ""

    def _load_token_stats(self) -> dict[str, int]:
        """Load per-task token stats from analytics."""
        import json
        from .state_paths import stats_path
        path = stats_path(self.workdir)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("tokens_by_task", {})
            return {k: int(v) for k, v in raw.items() if isinstance(v, (int, float))}
        except Exception:
            return {}

    def _teamlead_arbitrate(self, slot: SessionSlot, sid: str) -> None:
        """Handle looping/blocked cards. Decision-only protocol — no card file editing."""
        card = self._distributor.pick_teamlead_task(sid)
        if card is None:
            return
        # Skip if loop_count hasn't increased since last arbitration
        prev_arb = self._arbitrated_at_loop.get(card.id, -1)
        if card.loop_count <= prev_arb and card.action != Action.BLOCKED:
            self._distributor.release_card(card.id)
            return
        needs_esc = self._distributor.needs_escalation(card)
        if needs_esc:
            self.publisher._emit("escalate", card.id,
                                 f"{card.id} loop_count={card.loop_count}, "
                                 f"teamlead arbitrating before escalation")
        log_event(self.log_path, "INFO", "teamlead arbitration",
                  session_id=sid, task_id=card.id, loop_count=card.loop_count,
                  escalation_candidate=needs_esc)
        card.action = Action.ARBITRATION
        self._distributor.board.save_card(card)
        dec_path = _teamlead_decision_path(self.workdir)
        agent_log = self._find_latest_agent_log(card.id)
        prompt = build_teamlead_prompt(
            mode="arbitration", board=self._distributor.board, card=card,
            decision_path=str(dec_path), agent_log_path=agent_log,
            token_stats=self._load_token_stats(),
        )
        task = Task(task_id=card.id, text=f"[TL] {card.title}", done=False)
        slot.task = task
        try:
            result = self.engine.execute(self._make_request(task, prompt, self.workdir,
                                                            sid, False, 600.0))
            if result and result.status == "completed":
                self._process_teamlead_decision(dec_path)
                self._distributor.refresh()
                refreshed = self._distributor.board.card_by_id(card.id)
                if refreshed:
                    if refreshed.action == Action.BLOCKED:
                        self._escalate(refreshed)
                    elif refreshed.action == Action.ARBITRATION:
                        # Teamlead didn't set_action → safety fallback to Blocked
                        refreshed.action = Action.BLOCKED.value
                        self._distributor.board.save_card(refreshed)
                        log_event(self.log_path, "WARN",
                                  "teamlead left card in Arbitration, auto-blocking",
                                  task_id=card.id)
                        self._escalate(refreshed)
                    elif needs_esc:
                        # Escalation threshold reached but teamlead still "resolved" —
                        # force-block to stop infinite arbitration cycles
                        refreshed.action = Action.BLOCKED.value
                        self._distributor.board.save_card(refreshed)
                        log_event(self.log_path, "WARN",
                                  "force-blocking after escalation threshold",
                                  task_id=card.id, loop_count=refreshed.loop_count)
                        self._escalate(refreshed)
                    else:
                        # Resolved — record arbitration point, do NOT reset loop_count
                        self._arbitrated_at_loop[card.id] = card.loop_count
                        self.publisher._emit("arbitration", card.id,
                                             f"{card.id} teamlead resolved → {refreshed.action} "
                                             f"(loop_count={refreshed.loop_count})")
        finally:
            slot.task = None
            self._distributor.release_card(card.id)
        self.sleep_fn(3.0)

    # ── Teamlead: user directive handling ────────────────────────

    def _pop_directive(self) -> Optional[str]:
        with self._directive_lock:
            if self._directive_queue:
                return self._directive_queue.pop(0)
        return None

    def _teamlead_directive(self, slot: SessionSlot, sid: str, directive_text: str) -> None:
        """Run teamlead agent to process a user directive."""
        self.publisher._emit("directive", "", f"Teamlead processing: {directive_text}")
        log_event(self.log_path, "INFO", "teamlead directive start",
                  session_id=sid, directive=directive_text[:200])
        dec_path = _teamlead_decision_path(self.workdir)
        prompt = build_teamlead_prompt(
            mode="directive", board=self._distributor.board,
            directive_text=directive_text, decision_path=str(dec_path),
            token_stats=self._load_token_stats(),
        )
        task = Task(task_id="tl-directive", text=f"[TL] {directive_text[:40]}", done=False)
        slot.task = task
        try:
            result = self.engine.execute(self._make_request(task, prompt, self.workdir,
                                                            sid, False, 600.0))
            self._process_teamlead_decision(dec_path)
        finally:
            slot.task = None
        self.sleep_fn(2.0)

    # ── Teamlead: proactive board health check ───────────────────

    def _teamlead_health_check(self, slot: SessionSlot, sid: str) -> bool:
        """Run health check. Returns True if problems found and agent was invoked."""
        self._last_health_check = time.time()
        board = self._distributor.board
        deadlock = board.detect_wip_deadlock()
        starvation = ""
        if not deadlock:
            # Check starvation: remaining work exists but no worker can pick anything
            if self._distributor.has_remaining_work():
                diag = self._distributor.diagnose_no_work()
                if diag and "board empty" not in diag:
                    starvation = diag
        if not deadlock and not starvation:
            return False
        diagnostic = ""
        if deadlock:
            diagnostic += f"DEADLOCK: {deadlock}\n"
        if starvation:
            diagnostic += f"STARVATION: {starvation}\n"
        self.publisher._emit("escalate", "", f"[TL] Health check: {diagnostic.strip()}")
        log_event(self.log_path, "WARN", "board health issue detected",
                  session_id=sid, diagnostic=diagnostic[:500])
        dec_path = _teamlead_decision_path(self.workdir)
        prompt = build_teamlead_prompt(
            mode="health", board=self._distributor.board,
            diagnostic_info=diagnostic, decision_path=str(dec_path),
            token_stats=self._load_token_stats(),
        )
        task = Task(task_id="tl-health", text="[TL] Board health check", done=False)
        slot.task = task
        try:
            result = self.engine.execute(self._make_request(task, prompt, self.workdir,
                                                            sid, False, 600.0))
            self._process_teamlead_decision(dec_path)
        finally:
            slot.task = None
        self.sleep_fn(3.0)
        return True

    # ── Teamlead: decision file executor (shared by all modes) ───

    def _process_teamlead_decision(self, dec_path: Path) -> None:
        """Parse and execute a teamlead decision file if it exists."""
        from .teamlead_actions import execute_teamlead_actions, parse_teamlead_decision

        if not dec_path.exists():
            return
        try:
            decision = parse_teamlead_decision(dec_path)
            errors = execute_teamlead_actions(
                self._distributor.board, decision, self.publisher, self.log_path,
            )
            if errors:
                for e in errors:
                    self.publisher._emit("escalate", "", f"[TL] Action failed: {e}")
        except Exception as exc:
            self.publisher._emit("escalate", "", f"[TL] Decision parse failed: {exc}")
            log_event(self.log_path, "WARN", "teamlead decision parse failed", error=str(exc))
        finally:
            try:
                dec_path.unlink(missing_ok=True)
            except Exception:
                pass

    # ── Teamlead: anomaly detection ──────────────────────────────

    def _detect_anomaly(self) -> Optional[Incident]:
        """Check for crashed workers. Returns Incident or None.

        Only worker CRASHES (Python exceptions escaping ``_run_worker``) trigger
        incidents. Normal agent failures (validation errors, timeouts, stalls)
        are handled by the board's retry mechanism and loop-arbitration — they
        are expected operational events, not incidents.
        """
        with self._slots_lock:
            for slot in self._slots.values():
                if (slot.error
                        and slot.status == SlotStatus.CLOSED
                        and slot.session_id not in self._handled_crash_slots):
                    self._handled_crash_slots.add(slot.session_id)
                    self._incident_counter += 1
                    # Find the task and worktree that were being processed
                    task_id = slot.task.task_id if slot.task else ""
                    wt_path = slot.worktree.worktree_path if slot.worktree else ""
                    return Incident(
                        id=f"INC-{self._incident_counter:03d}",
                        phase=IncidentPhase.SCALE_DOWN,
                        error_type="worker_crash",
                        source_task_id=task_id,
                        source_slot_id=slot.session_id,
                        error_message=slot.error,
                        traceback=slot.crash_traceback,
                        worktree_path=wt_path,
                    )

        return None

    # ── Teamlead: incident state machine ─────────────────────────

    def _process_incident(self, slot: SessionSlot, incident: Incident) -> Optional[Incident]:
        """Process one step of the incident state machine. Returns updated incident or None if resolved."""
        phase = incident.phase

        if phase == IncidentPhase.SCALE_DOWN:
            return self._incident_scale_down(incident)

        if phase == IncidentPhase.TRIAGE:
            return self._incident_triage(slot, incident)

        if phase == IncidentPhase.INJECT_FIX:
            return self._incident_inject_fix(incident)

        if phase == IncidentPhase.WAIT_FOR_FIX:
            return self._incident_wait_for_fix(incident)

        if phase == IncidentPhase.SCALE_UP:
            return self._incident_scale_up(incident)

        if phase == IncidentPhase.NOTIFY_HUMAN:
            return self._incident_notify_human(incident)

        # Unknown phase — should not happen
        log_event(self.log_path, "ERROR", "unknown incident phase",
                  incident_id=incident.id, phase=str(phase))
        return None

    def _incident_scale_down(self, incident: Incident) -> Incident:
        """Scale down workers to 1, then move to TRIAGE."""
        original_count, removed_ids = self._scale_down_workers(keep=1)
        # Use intended worker count (max_sessions - 1 for teamlead) if all workers
        # already crashed, so scale_up restores the correct number.
        intended_count = self.max_sessions - 1
        incident.original_worker_count = max(original_count, intended_count)
        incident.removed_session_ids = removed_ids
        self.publisher.log_incident(
            incident.id,
            f"Scaling down: {original_count} → 1 worker (removed {len(removed_ids)})",
        )
        log_event(self.log_path, "INFO", "incident scale_down",
                  incident_id=incident.id, original=original_count, removed=len(removed_ids))
        if removed_ids:
            self._wait_slots_closed(removed_ids, timeout=SCALE_DOWN_WAIT_TIMEOUT)
        incident.phase = IncidentPhase.TRIAGE
        return incident

    def _incident_triage(self, slot: SessionSlot, incident: Incident) -> Incident:
        """Run AI agent for triage analysis."""
        sid = slot.session_id
        board = self._distributor.board
        source_card = board.card_by_id(incident.source_task_id) if incident.source_task_id else None

        orc_root = Path(self.workdir) / ".orc"
        orc_root.mkdir(parents=True, exist_ok=True)
        decision_path = orc_root / DECISION_FILENAME

        prompt = build_incident_prompt(incident, board, source_card, str(decision_path), orc_root)
        task = Task(task_id=f"triage-{incident.id}", text=f"[TL] Triage {incident.id}", done=False)
        slot.task = task

        self.publisher.log_incident(incident.id, "Running AI triage agent...")
        result = self.engine.execute(self._make_request(task, prompt, self.workdir,
                                                        sid, False, 600.0))

        # Parse the decision
        try:
            if result and result.status == "completed" and decision_path.exists():
                decision = parse_incident_decision(decision_path)
            else:
                self.publisher.log_incident(incident.id, "AI triage failed, using fallback")
                log_event(self.log_path, "WARN", "triage agent failed, using fallback",
                          incident_id=incident.id)
                decision = fallback_decision(incident)
        except Exception as exc:
            self.publisher.log_incident(incident.id, f"Decision parse failed: {exc}, using fallback")
            log_event(self.log_path, "WARN", "decision parse failed",
                      incident_id=incident.id, error=str(exc),
                      error_type=type(exc).__name__)
            decision = fallback_decision(incident)
        finally:
            # Cleanup decision and traceback files
            for cleanup_path in (decision_path, orc_root / "incident-traceback.txt"):
                if cleanup_path.exists():
                    try:
                        cleanup_path.unlink()
                    except OSError:
                        pass

        incident.error_class = decision.classification
        incident.target_role = decision.target_role
        incident.fix_title = decision.fix_title
        incident.fix_body = decision.body

        self.publisher.log_incident(
            incident.id,
            f"Triage result: {decision.classification}, role={decision.target_role}, "
            f"title={decision.fix_title[:80]}",
        )
        log_event(self.log_path, "INFO", "triage complete",
                  incident_id=incident.id, classification=decision.classification,
                  target_role=decision.target_role)

        if decision.classification == "orc":
            incident.phase = IncidentPhase.NOTIFY_HUMAN
        else:
            incident.phase = IncidentPhase.INJECT_FIX
        return incident

    def _incident_inject_fix(self, incident: Incident) -> Incident:
        """Create an expedite fix card and place it on the board."""
        board = self._distributor.board
        # Include incident ID to avoid duplicate card IDs if the same task
        # triggers multiple incidents across time.
        base = incident.source_task_id or "unknown"
        fix_card_id = f"{FIX_CARD_PREFIX}{base}-{incident.id}"

        # Map target_role to the correct stage+action so the pull system
        # assigns the card to the right role.
        _ROLE_PLACEMENT: dict[str, tuple[str, str]] = {
            "coder":      ("4_Coding",  Action.CODING),
            "architect":  ("2_Estimate", Action.ARCHITECT),
            "reviewer":   ("5_Review",  Action.REVIEWING),
            "integrator": ("7_Handoff", Action.INTEGRATING),
        }
        stage, action = _ROLE_PLACEMENT.get(incident.target_role, ("4_Coding", Action.CODING))

        card = board.create_expedite_card(
            card_id=fix_card_id,
            title=incident.fix_title,
            body=incident.fix_body,
            stage=stage,
            action=action,
            cos_justification=f"Incident {incident.id}: {incident.error_type}",
        )
        incident.fix_card_id = fix_card_id
        incident.fix_started_at = time.time()

        self.publisher.log_incident(
            incident.id,
            f"Fix card {fix_card_id} created in {stage} (role={incident.target_role})",
        )
        log_event(self.log_path, "INFO", "fix card injected",
                  incident_id=incident.id, fix_card_id=fix_card_id,
                  stage=stage, target_role=incident.target_role)

        incident.phase = IncidentPhase.WAIT_FOR_FIX
        return incident

    def _incident_wait_for_fix(self, incident: Incident) -> Optional[Incident]:
        """Poll the fix card until done, failed, or timed out."""
        board = self._distributor.board
        fix_card = board.card_by_id(incident.fix_card_id)

        if fix_card and fix_card.stage == "8_Done":
            self.publisher.log_incident(incident.id, f"Fix {incident.fix_card_id} completed!")
            log_event(self.log_path, "INFO", "fix completed",
                      incident_id=incident.id, fix_card_id=incident.fix_card_id)
            incident.phase = IncidentPhase.SCALE_UP
            return incident

        # Check if fix card itself failed
        if incident.fix_card_id in self._failed_tasks:
            self.publisher.log_incident(
                incident.id,
                f"Fix card {incident.fix_card_id} itself failed — escalating to human",
            )
            self._block_fix_card(incident)
            self._send_incident_telegram(
                incident,
                f"Fix card {incident.fix_card_id} failed while trying to resolve "
                f"incident {incident.id}.\n"
                f"Original error: {incident.error_message[:500]}",
            )
            # Scale back up before returning — don't leave workers down
            self._scale_up_workers(incident.original_worker_count)
            return None

        # Check timeout
        elapsed = time.time() - incident.fix_started_at
        if elapsed > INCIDENT_FIX_TIMEOUT:
            self.publisher.log_incident(
                incident.id,
                f"Fix timeout ({INCIDENT_FIX_TIMEOUT:.0f}s) — escalating to human",
            )
            self._block_fix_card(incident)
            self._send_incident_telegram(
                incident,
                f"Fix card {incident.fix_card_id} timed out after {elapsed:.0f}s.\n"
                f"Incident {incident.id}: {incident.error_message[:500]}",
            )
            # Scale back up
            self._scale_up_workers(incident.original_worker_count)
            return None

        return incident  # Keep waiting

    def _incident_scale_up(self, incident: Incident) -> None:
        """Restore workers to original count."""
        new_ids = self._scale_up_workers(incident.original_worker_count)
        self.publisher.log_incident(
            incident.id,
            f"Scaling up: restored to {incident.original_worker_count} workers "
            f"(added {len(new_ids)})",
        )
        log_event(self.log_path, "INFO", "incident scale_up",
                  incident_id=incident.id, target=incident.original_worker_count,
                  added=len(new_ids))
        return None  # Incident resolved

    def _incident_notify_human(self, incident: Incident) -> None:
        """Send ORC error details to Telegram and block the source card.

        Workers stay scaled down — if the ORC bug is in a common code path,
        scaling up would cause a crash loop. The human must fix ORC and restart.
        """
        self.publisher.log_incident(incident.id, "ORC error — notifying human via Telegram")

        # Send the AI-written message (or a fallback)
        message = incident.fix_body or (
            f"ORC BUG in incident {incident.id}\n"
            f"Error: {incident.error_message}\n"
            f"Traceback:\n{incident.traceback[:1500]}"
        )
        self._send_incident_telegram(incident, message)

        # Block the source card if it exists
        if incident.source_task_id:
            board = self._distributor.board
            card = board.card_by_id(incident.source_task_id)
            if card and card.action != Action.BLOCKED:
                card.action = Action.BLOCKED
                board.save_card(card)
                self._distributor.release_card(card.id)

        # Do NOT scale workers back up for ORC errors — the bug is in ORC's
        # own code path and workers would hit the same crash on every task.
        # The human must fix ORC and restart the orchestrator.

        log_event(self.log_path, "WARN", "orc error notified, workers remain scaled down",
                  incident_id=incident.id, source_task=incident.source_task_id)
        return None  # Incident handled (human will fix ORC)

    def _block_fix_card(self, incident: Incident) -> None:
        """Block the fix card so workers don't retry it after scale-up."""
        board = self._distributor.board
        fix_card = board.card_by_id(incident.fix_card_id)
        if fix_card and fix_card.action != Action.BLOCKED:
            fix_card.action = Action.BLOCKED
            board.save_card(fix_card)
            self._distributor.release_card(fix_card.id)

    def _send_incident_telegram(self, incident: Incident, message: str) -> None:
        """Send an incident-related Telegram notification."""
        header = f"INCIDENT {incident.id} ({incident.error_type})\n"
        send_telegram_message(
            header + message,
            self.log_path,
            orc_root=Path(self.workdir),
        )

    # ── Teamlead: worker scaling ─────────────────────────────────

    def _scale_down_workers(self, keep: int = 1) -> tuple[int, list[str]]:
        """Scale down to `keep` workers. Returns (original_count, removed_session_ids)."""
        with self._slots_lock:
            worker_slots = [
                s for s in self._slots.values()
                if (s.role or "worker") == "worker"
                and s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
            ]
        original_count = len(worker_slots)
        if original_count <= keep:
            return original_count, []

        # Keep RUNNING slots first (they're mid-task), remove IDLE slots first
        worker_slots.sort(key=lambda s: (0 if s.status == SlotStatus.RUNNING else 1))
        to_remove = worker_slots[keep:]

        removed_ids = []
        for s in to_remove:
            self.request_remove_session(s.session_id)
            removed_ids.append(s.session_id)
        return original_count, removed_ids

    def _wait_slots_closed(self, session_ids: list[str], timeout: float = 60.0) -> bool:
        """Wait for specific slots to reach CLOSED status."""
        deadline = time.time() + timeout
        remaining = set(session_ids)
        while remaining and time.time() < deadline:
            with self._slots_lock:
                still_open = {
                    sid for sid in remaining
                    if sid in self._slots and self._slots[sid].status not in (SlotStatus.CLOSED,)
                }
            remaining = still_open
            if remaining:
                self.sleep_fn(1.0)
        return len(remaining) == 0

    def _scale_up_workers(self, target_count: int) -> list[str]:
        """Add workers until we reach target_count active workers."""
        with self._slots_lock:
            current_workers = sum(
                1 for s in self._slots.values()
                if (s.role or "worker") == "worker"
                and s.status in (SlotStatus.IDLE, SlotStatus.RUNNING)
            )
        new_ids = []
        to_add = max(0, target_count - current_workers)
        for _ in range(to_add):
            if is_stop_requested():
                break
            sid = self.request_add_session()
            if sid:
                new_ids.append(sid)
            self.sleep_fn(STAGGER_DELAY_SECONDS)
        return new_ids

    def _escalate(self, card: KanbanCard) -> None:
        card.action = "Blocked"
        self._distributor.board.save_card(card)
        msg = (f"ESCALATION: Task {card.id} ({card.title}) blocked. "
               f"Loop count: {card.loop_count}. Stage: {card.stage}.")
        self.publisher.log_escalate(card.id, msg)
        send_telegram_message(
            f"🚨 {card.id} BLOCKED\n"
            f"  {card.title}\n"
            f"  Stage: {card.stage}, loops: {card.loop_count}\n"
            f"  Use /unblock {card.id} <directive> to resume",
            self.log_path,
            orc_root=Path(self.workdir),
        )
        log_event(self.log_path, "WARN", "escalation", task_id=card.id, message=msg)

    def _notify_completion(
        self, card: KanbanCard, role: str,
        old_stage: str, old_action: str, old_cos: str,
        elapsed: float,
    ) -> None:
        """Send a single rich Telegram notification after a role finishes."""
        mins = elapsed / 60.0
        new_stage = card.stage
        new_action = card.action

        # Only notify on meaningful transitions, not every micro-step
        # Notify: stage changed, or expedite flagged, or Done
        stage_changed = old_stage != new_stage
        became_expedite = card.class_of_service == "expedite" and old_cos != "expedite"
        is_done = new_stage == "8_Done"

        if not stage_changed and not became_expedite:
            return

        # Build short stage names for readability
        short = {"1_Inbox": "Inbox", "2_Estimate": "Estimate", "3_Todo": "Todo",
                 "4_Coding": "Coding", "5_Review": "Review", "6_Testing": "Testing",
                 "7_Handoff": "Handoff", "8_Done": "Done"}
        fr = short.get(old_stage, old_stage)
        to = short.get(new_stage, new_stage)

        icon = "✅" if is_done else "🔄"
        if became_expedite:
            icon = "🔥"

        lines = [f"{icon} {card.id}: {card.title}"]
        lines.append(f"  {role} ({mins:.0f}m): {fr} → {to}")
        if old_action != new_action:
            lines.append(f"  Action: {old_action} → {new_action}")
        if became_expedite:
            lines.append(f"  EXPEDITE: {card.cos_justification or 'no reason'}")

        # Add progress
        done, _ip, total = self._distributor.get_progress()
        lines.append(f"  Progress: {done}/{total}")

        send_telegram_message("\n".join(lines), self.log_path, orc_root=Path(self.workdir))

    # ── Request builder ──────────────────────────────────────────

    def _make_request(self, task, prompt, workdir, session_id, commit_phase, task_ttl):
        def _pub(snapshot: MonitorSnapshot) -> None:
            self._session_snapshots[session_id] = snapshot
            if self.snapshot_publisher:
                self.snapshot_publisher(session_id, snapshot)
        return build_kanban_request(
            task=task, prompt=prompt, workdir=workdir, base_workdir=self.workdir,
            tasks_dir=self.tasks_dir, session_id=session_id, commit_phase=commit_phase,
            task_ttl=task_ttl, args=self.args, backend=self.backend,
            commit_template=self.commit_template, merge_expert_template=self.merge_expert_template,
            merge_expert_model=self.merge_expert_model, main_branch=self.main_branch,
            progress=self._distributor.get_progress(), snapshot_publisher=_pub,
        )

    # ── Inbox ────────────────────────────────────────────────────

    def add_inbox_card(self, text: str) -> None:
        board = self._distributor.board
        card_id = board.next_card_id()
        card = board.create_inbox_card(card_id, text)
        self.publisher.log_inbox(card_id, text)
        log_event(self.log_path, "INFO", "inbox card created", card_id=card_id, title=text)

    # ── Human-in-the-loop ─────────────────────────────────────────

    def unblock_card(self, card_id: str, directive: str) -> None:
        """Unblock a card and send it back to Coding with a directive."""
        board = self._distributor.board
        card = board.card_by_id(card_id)
        if card is None:
            return
        if card.action != Action.BLOCKED:
            return
        if directive:
            card.body += f"\n\n## Human Directive\n{directive}\n"
        card.action = Action.CODING
        card.loop_count = 0
        board.save_card(card)
        self.publisher.log_unblock(card_id, directive)
        log_event(self.log_path, "INFO", "card unblocked", card_id=card_id, directive=directive)

    def queue_teamlead_directive(self, text: str) -> None:
        """Queue a user directive for the teamlead to process."""
        with self._directive_lock:
            self._directive_queue.append(text)
        self.publisher._emit("directive", "", f"Directive queued for teamlead: {text}")
        log_event(self.log_path, "INFO", "teamlead directive queued", directive=text[:200])

    # ── Helpers ──────────────────────────────────────────────────

    def _should_continue(self, slot: SessionSlot) -> bool:
        return (not is_stop_requested()
                and not is_session_stop_requested(slot.session_id)
                and slot.status != SlotStatus.CLOSING)

    def _board_diag_short(self) -> str:
        """One-line board summary for diagnostics."""
        board = self._distributor.board
        inbox = board.cards_in_stage("1_Inbox")
        free_inbox = sum(1 for c in inbox if not c.assigned_agent)
        total_assigned = sum(1 for c in board.cards if c.assigned_agent)
        return f"inbox={len(inbox)} (free={free_inbox}), assigned_total={total_assigned}"

    def _shutdown_all(self) -> None:
        with self._slots_lock:
            for s in self._slots.values():
                s.status = SlotStatus.CLOSING
            threads = [(s.session_id, s.thread) for s in self._slots.values() if s.thread]
        total = len(threads)
        if total:
            self.publisher._emit("system", "", f"Shutting down {total} agents...")
        for i, (sid, t) in enumerate(threads, 1):
            self.publisher._emit("system", "", f"Waiting for {sid} ({i}/{total})...")
            t.join(timeout=SHUTDOWN_JOIN_TIMEOUT_SECONDS)
            if t.is_alive():
                self.publisher._emit("system", "", f"{sid} still running, skipping")
            else:
                self.publisher._emit("system", "", f"{sid} stopped ({total - i} remaining)")
        if total:
            self.publisher._emit("system", "", "All agents stopped")
