#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead runner: orchestrates board health, arbitration, and directives."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from .kanban_card import KanbanCard
from .kanban_constants import Action
from .task_execution_types import TaskExecutionStatus
from .kanban_distributor import KanbanDistributor
from .kanban_incident_manager import IncidentManager
from .kanban_protocols import DirectiveSource, RunnerLifecycle, RunnerNotifier, RunnerStateManager
from .kanban_publisher import KanbanPublisher
from .kanban_roles import build_teamlead_prompt
from .logging import log_event
from .quit_signal import is_quit_after_task_requested
from .session_types import SessionSlot, SlotStatus
from .task_execution import TaskExecutionEngine
from .task_source import Task
from .teamlead_incident import Incident

_logger = logging.getLogger(__name__)


def _teamlead_decision_path(workdir: str) -> Path:
    """Return the standard teamlead decision file path."""
    p = Path(workdir) / ".orc"
    p.mkdir(parents=True, exist_ok=True)
    return p / "teamlead-decision.md"


class KanbanTeamleadRunner:
    """Runs the teamlead agent loop: directives, anomalies, health checks, arbitration."""

    _HEALTH_CHECK_INTERVAL_BASE = 300.0
    _HEALTH_CHECK_INTERVAL_MAX = 1800.0
    _AUTO_COMMIT_INTERVAL = 120.0

    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine: TaskExecutionEngine,
        distributor: KanbanDistributor,
        publisher: KanbanPublisher,
        incident_mgr: IncidentManager,
        slots_lock: threading.Lock,
        arbitrated_at_loop: dict[str, int],
        lifecycle: RunnerLifecycle,
        notifier: RunnerNotifier,
        state_manager: RunnerStateManager,
        directives: DirectiveSource,
    ) -> None:
        self._workdir = workdir
        self._log_path = log_path
        self._engine = engine
        self._distributor = distributor
        self._publisher = publisher
        self._incident_mgr = incident_mgr
        self._slots_lock = slots_lock
        self._arbitrated_at_loop = arbitrated_at_loop
        self._lifecycle = lifecycle
        self._notifier = notifier
        self._state_manager = state_manager
        self._directives = directives

        self._last_health_check: float = 0.0
        self._consecutive_health_checks: int = 0
        self._last_health_diagnostic: str = ""
        self._last_auto_commit: float = 0.0

    # ── Main loop ───────────────────────────────────────────────

    def run(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self._publisher._emit("system", "", f"{sid} teamlead started, monitoring board...")
        incident: Optional[Incident] = None
        try:
            while self._lifecycle.should_continue(slot):
                self._distributor.refresh()
                self._distributor.board._apply_deferred_moves()
                if incident is not None:
                    incident = self._incident_mgr.process_incident(slot, incident)
                    if incident is None:
                        self._publisher._emit("incident", "",
                                               "Incident resolved, resuming normal operations")
                    self._lifecycle.sleep(2.0)
                    if is_quit_after_task_requested():
                        self._publisher._emit("system", "", f"{sid} teamlead exiting (quit-after-task)")
                        break
                    continue

                directive = self._directives.pop_directive()
                if directive:
                    self.directive(slot, sid, directive)
                    continue

                anomaly = self._incident_mgr.detect_anomaly()
                if anomaly is not None:
                    incident = anomaly
                    self._publisher.log_incident(
                        incident.id,
                        f"{incident.error_type} on {incident.source_task_id or incident.source_slot_id}: "
                        f"{incident.error_message[:200]}",
                    )
                    log_event(self._log_path, "WARN", "incident detected",
                              incident_id=incident.id, error_type=incident.error_type,
                              source_task=incident.source_task_id, source_slot=incident.source_slot_id)
                    continue

                health_interval = min(
                    self._HEALTH_CHECK_INTERVAL_BASE * (2 ** self._consecutive_health_checks),
                    self._HEALTH_CHECK_INTERVAL_MAX,
                )
                if time.time() - self._last_health_check >= health_interval:
                    if self.health_check(slot, sid):
                        continue

                self.arbitrate(slot, sid)
                self.auto_commit_cards()

                if not self._distributor.has_remaining_work():
                    self._publisher._emit("system", "", f"{sid} teamlead: no remaining work")
                    break
                self._lifecycle.sleep(5.0)
                if is_quit_after_task_requested():
                    self._publisher._emit("system", "", f"{sid} teamlead exiting (quit-after-task)")
                    break
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.error = f"teamlead_crashed:{type(exc).__name__}"
            log_event(self._log_path, "ERROR", "teamlead crashed",
                      session_id=sid, error=str(exc),
                      traceback=traceback.format_exc()[:2000])
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    # ── Arbitration ─────────────────────────────────────────────

    def arbitrate(self, slot: SessionSlot, sid: str) -> None:
        """Handle looping/blocked cards. Decision-only protocol."""
        card = self._distributor.pick_teamlead_task(sid)
        if card is None:
            return
        prev_arb = self._arbitrated_at_loop.get(card.id, -1)
        if card.loop_count <= prev_arb:
            self._distributor.release_card(card.id)
            return
        needs_esc = self._distributor.needs_escalation(card)
        if needs_esc:
            self._publisher._emit("escalate", card.id,
                                   f"{card.id} loop_count={card.loop_count}, "
                                   f"teamlead arbitrating before escalation")
        log_event(self._log_path, "INFO", "teamlead arbitration",
                  session_id=sid, task_id=card.id, loop_count=card.loop_count,
                  escalation_candidate=needs_esc)
        card.action = Action.ARBITRATION
        self._distributor.board.save_card(card)
        dec_path = _teamlead_decision_path(self._workdir)
        agent_log = self.find_latest_agent_log(card.id)
        prompt = build_teamlead_prompt(
            mode="arbitration", board=self._distributor.board, card=card,
            decision_path=str(dec_path), agent_log_path=agent_log,
            token_stats=self.load_token_stats(),
        )
        task = Task(task_id=card.id, text=f"[TL] {card.title}", done=False)
        slot.task = task
        try:
            result = self._engine.execute(self._state_manager.make_request(task, prompt, self._workdir,
                                                              sid, False, 600.0))
            if result and result.status == TaskExecutionStatus.COMPLETED:
                self.process_decision(dec_path)
                self._distributor.refresh()
                refreshed = self._distributor.board.card_by_id(card.id)
                if refreshed:
                    if refreshed.action == Action.BLOCKED:
                        self.escalate(refreshed)
                    elif refreshed.action == Action.ARBITRATION:
                        refreshed.action = Action.BLOCKED.value
                        self._distributor.board.save_card(refreshed)
                        log_event(self._log_path, "WARN",
                                  "teamlead left card in Arbitration, auto-blocking",
                                  task_id=card.id)
                        self.escalate(refreshed)
                    elif needs_esc:
                        self._arbitrated_at_loop[card.id] = card.loop_count
                        self._state_manager.mark_dirty()
                        log_event(self._log_path, "INFO",
                                  "escalation threshold reached but teamlead resolved — allowing progress",
                                  task_id=card.id, loop_count=refreshed.loop_count,
                                  action=refreshed.action, stage=refreshed.stage)
                    else:
                        self._arbitrated_at_loop[card.id] = card.loop_count
                        self._state_manager.mark_dirty()
                        self._publisher._emit("arbitration", card.id,
                                               f"{card.id} teamlead resolved → {refreshed.action} "
                                               f"(loop_count={refreshed.loop_count})")
        finally:
            slot.task = None
            self._distributor.release_card(card.id)
        self._lifecycle.sleep(3.0)

    # ── Directive handling ──────────────────────────────────────

    def directive(self, slot: SessionSlot, sid: str, directive_text: str) -> None:
        """Run teamlead agent to process a user directive."""
        self._publisher._emit("directive", "", f"Teamlead processing: {directive_text}")
        log_event(self._log_path, "INFO", "teamlead directive start",
                  session_id=sid, directive=directive_text[:200])
        dec_path = _teamlead_decision_path(self._workdir)
        prompt = build_teamlead_prompt(
            mode="directive", board=self._distributor.board,
            directive_text=directive_text, decision_path=str(dec_path),
            token_stats=self.load_token_stats(),
        )
        task = Task(task_id="tl-directive", text=f"[TL] {directive_text[:40]}", done=False)
        slot.task = task
        try:
            result = self._engine.execute(self._state_manager.make_request(task, prompt, self._workdir,
                                                              sid, False, 600.0))
            self.process_decision(dec_path)
        finally:
            slot.task = None
        self._lifecycle.sleep(2.0)

    # ── Health check ────────────────────────────────────────────

    def health_check(self, slot: SessionSlot, sid: str) -> bool:
        """Run health check. Returns True if problems found and agent was invoked."""
        self._last_health_check = time.time()
        board = self._distributor.board
        deadlock = board.detect_wip_deadlock()
        starvation = ""
        if not deadlock:
            if self._distributor.has_remaining_work():
                diag = self._distributor.diagnose_no_work()
                if diag and "board empty" not in diag:
                    starvation = diag
        if not deadlock and not starvation:
            self._consecutive_health_checks = 0
            self._last_health_diagnostic = ""
            return False
        if starvation and not deadlock:
            all_dep_blocked = all(
                "unmet deps" in line or "action=Blocked" in line
                or "no matching role" in line
                for line in starvation.split(";") if line.strip()
            )
            if all_dep_blocked:
                log_event(self._log_path, "INFO", "health check: dep-only starvation, skipping AI",
                          session_id=sid)
                return False
        diagnostic = ""
        if deadlock:
            diagnostic += f"DEADLOCK: {deadlock}\n"
        if starvation:
            diagnostic += f"STARVATION: {starvation}\n"
        if diagnostic == self._last_health_diagnostic and self._consecutive_health_checks > 0:
            self._consecutive_health_checks += 1
            log_event(self._log_path, "INFO",
                      "health check: same diagnostic as last time, skipping AI",
                      session_id=sid, consecutive=self._consecutive_health_checks)
            return False
        self._last_health_diagnostic = diagnostic
        self._consecutive_health_checks += 1
        self._publisher._emit("escalate", "", f"[TL] Health check: {diagnostic.strip()}")
        log_event(self._log_path, "WARN", "board health issue detected",
                  session_id=sid, diagnostic=diagnostic[:500])
        dec_path = _teamlead_decision_path(self._workdir)
        prompt = build_teamlead_prompt(
            mode="health", board=self._distributor.board,
            diagnostic_info=diagnostic, decision_path=str(dec_path),
            token_stats=self.load_token_stats(),
        )
        task = Task(task_id="tl-health", text="[TL] Board health check", done=False)
        slot.task = task
        try:
            result = self._engine.execute(self._state_manager.make_request(task, prompt, self._workdir,
                                                              sid, False, 600.0))
            self.process_decision(dec_path)
        finally:
            slot.task = None
        self._lifecycle.sleep(3.0)
        return True

    # ── Decision file executor ──────────────────────────────────

    def process_decision(self, dec_path: Path) -> None:
        """Parse and execute a teamlead decision file if it exists."""
        from .teamlead_actions import execute_teamlead_actions, parse_teamlead_decision

        if not dec_path.exists():
            return
        try:
            decision = parse_teamlead_decision(dec_path)
            errors = execute_teamlead_actions(
                self._distributor.board, decision, self._publisher, self._log_path,
            )
            if errors:
                for e in errors:
                    self._publisher._emit("escalate", "", f"[TL] Action failed: {e}")
        except Exception as exc:
            self._publisher._emit("escalate", "", f"[TL] Decision parse failed: {exc}")
            log_event(self._log_path, "WARN", "teamlead decision parse failed", error=str(exc))
        finally:
            try:
                dec_path.unlink(missing_ok=True)
            except OSError:
                pass

    # ── Escalation ──────────────────────────────────────────────

    def escalate(self, card: KanbanCard) -> None:
        card.action = "Blocked"
        self._distributor.board.save_card(card)
        self._arbitrated_at_loop[card.id] = card.loop_count
        self._state_manager.mark_dirty()
        msg = (f"ESCALATION: Task {card.id} ({card.title}) blocked. "
               f"Loop count: {card.loop_count}. Stage: {card.stage}.")
        self._publisher.log_escalate(card.id, msg)
        self._notifier.send_telegram(
            f"\U0001f6a8 {card.id} BLOCKED\n"
            f"  {card.title}\n"
            f"  Stage: {card.stage}, loops: {card.loop_count}\n"
            f"  Use /unblock {card.id} <directive> to resume"
        )
        log_event(self._log_path, "WARN", "escalation", task_id=card.id, detail=msg)

    # ── Helpers ─────────────────────────────────────────────────

    def find_latest_agent_log(self, card_id: str) -> str:
        """Find the most recent raw-stream log for a card across all kanban sessions."""
        from .state_paths import run_root
        runs_dir = run_root(self._workdir, "").parent / "runs"
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

    def load_token_stats(self) -> dict[str, int]:
        """Load per-task token stats from analytics."""
        import json
        from .state_paths import stats_path
        path = stats_path(self._workdir)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("tokens_by_task", {})
            return {k: int(v) for k, v in raw.items() if isinstance(v, (int, float))}
        except Exception:
            return {}

    def auto_commit_cards(self) -> None:
        """Periodically git-add+commit all changes to keep base repo clean."""
        now = time.time()
        if now - self._last_auto_commit < self._AUTO_COMMIT_INTERVAL:
            return
        self._last_auto_commit = now
        try:
            from .worktree_flow import run_git
            wd = self._workdir
            ok, stdout, _, _ = run_git(wd, ["git", "status", "--porcelain"])
            if not ok or not stdout.strip():
                return
            run_git(wd, ["git", "add", "-A"])
            run_git(wd, ["git", "commit", "-m", "chore: sync board state and project files"])
            log_event(self._log_path, "INFO", "auto-committed workspace state")
        except Exception as exc:
            log_event(self._log_path, "WARN", "auto-commit failed", error=str(exc))
