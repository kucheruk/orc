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

from ..board.kanban_card import KanbanCard
from ..board.action_constants import Action
from ..models.task_status import TaskExecutionStatus
from ..incident.manager import IncidentManager
from ..supervision.outcomes import TaskOutcomeTracker
from .kanban_protocols import DirectiveSource, EventPublisher, RunnerLifecycle, RunnerNotifier, RunnerStateManager, WorkDistributor
from .kanban_roles import build_teamlead_prompt
from .teamlead_stats import find_latest_agent_log, load_token_stats
from ..git.git_helpers import run_git
from ..log import log_event
from ..quit_signal import is_quit_after_task_requested
from ..models.session_types import SessionSlot, SlotStatus
from .teamlead_actions import execute_teamlead_actions, parse_teamlead_decision
from .kanban_protocols import TaskExecutor
from ..models.task_dto import Task
from ..incident.domain import Incident

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
        engine: TaskExecutor,
        distributor: WorkDistributor,
        publisher: EventPublisher,
        incident_mgr: IncidentManager,
        slots_lock: threading.Lock,
        outcomes: TaskOutcomeTracker,
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
        self._outcomes = outcomes
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
            slot.mark_crashed(exc, traceback.format_exc())
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
        prev_arb = self._outcomes.get_arbitrated_loop(card.id)
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
        agent_log = find_latest_agent_log(self._workdir, card.id)
        prompt = build_teamlead_prompt(
            mode="arbitration", board=self._distributor.board, card=card,
            decision_path=str(dec_path), agent_log_path=agent_log,
            token_stats=load_token_stats(self._workdir),
        )
        task = Task(task_id=card.id, text=f"[TL] {card.title}", done=False)
        try:
            result = self._invoke_teamlead(slot, sid, task, prompt)
            if result and result.status == TaskExecutionStatus.COMPLETED:
                self.process_decision(dec_path)
                self._distributor.refresh()
                refreshed = self._distributor.board.card_by_id(card.id)
                if refreshed:
                    if refreshed.action == Action.BLOCKED:
                        self.escalate(refreshed)
                    elif refreshed.action == Action.ARBITRATION:
                        refreshed.block()
                        self._distributor.board.save_card(refreshed)
                        log_event(self._log_path, "WARN",
                                  "teamlead left card in Arbitration, auto-blocking",
                                  task_id=card.id)
                        self.escalate(refreshed)
                    elif needs_esc:
                        self._outcomes.set_arbitrated_loop(card.id, card.loop_count)
                        log_event(self._log_path, "INFO",
                                  "escalation threshold reached but teamlead resolved — allowing progress",
                                  task_id=card.id, loop_count=refreshed.loop_count,
                                  action=refreshed.action, stage=refreshed.stage)
                    else:
                        self._outcomes.set_arbitrated_loop(card.id, card.loop_count)
                        self._publisher._emit("arbitration", card.id,
                                               f"{card.id} teamlead resolved → {refreshed.action} "
                                               f"(loop_count={refreshed.loop_count})")
        finally:
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
            token_stats=load_token_stats(self._workdir),
        )
        task = Task(task_id="tl-directive", text=f"[TL] {directive_text[:40]}", done=False)
        self._invoke_teamlead(slot, sid, task, prompt)
        self.process_decision(dec_path)
        self._lifecycle.sleep(2.0)

    # ── Health check ────────────────────────────────────────────

    def health_check(self, slot: SessionSlot, sid: str) -> bool:
        """Run health check. Returns True if problems found and agent was invoked."""
        from ..use_cases.check_board_health import diagnose_board_health, should_skip_repeated_diagnostic

        self._last_health_check = time.time()
        diagnostic = diagnose_board_health(self._distributor.board, self._distributor)
        if diagnostic is None:
            self._consecutive_health_checks = 0
            self._last_health_diagnostic = ""
            return False
        if diagnostic.is_dependency_only_starvation:
            log_event(self._log_path, "INFO", "health check: dep-only starvation, skipping AI",
                      session_id=sid)
            return False
        if should_skip_repeated_diagnostic(diagnostic, self._last_health_diagnostic, self._consecutive_health_checks):
            self._consecutive_health_checks += 1
            log_event(self._log_path, "INFO",
                      "health check: same diagnostic as last time, skipping AI",
                      session_id=sid, consecutive=self._consecutive_health_checks)
            return False
        self._last_health_diagnostic = diagnostic.summary
        self._consecutive_health_checks += 1
        diag_text = diagnostic.summary
        self._publisher._emit("escalate", "", f"[TL] Health check: {diag_text.strip()}")
        log_event(self._log_path, "WARN", "board health issue detected",
                  session_id=sid, diagnostic=diag_text[:500])
        dec_path = _teamlead_decision_path(self._workdir)
        prompt = build_teamlead_prompt(
            mode="health", board=self._distributor.board,
            diagnostic_info=diag_text, decision_path=str(dec_path),
            token_stats=load_token_stats(self._workdir),
        )
        task = Task(task_id="tl-health", text="[TL] Board health check", done=False)
        self._invoke_teamlead(slot, sid, task, prompt)
        self.process_decision(dec_path)
        self._lifecycle.sleep(3.0)
        return True

    # ── Decision file executor ──────────────────────────────────

    def process_decision(self, dec_path: Path) -> None:
        """Parse and execute a teamlead decision file if it exists."""
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
        card.block()
        self._distributor.board.save_card(card)
        self._outcomes.set_arbitrated_loop(card.id, card.loop_count)
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

    def _invoke_teamlead(self, slot: SessionSlot, sid: str, task: Task, prompt: str):
        """Shared scaffolding: attach task to slot, run engine, always detach."""
        slot.task = task
        try:
            return self._engine.execute(
                self._state_manager.make_request(task, prompt, self._workdir, sid, False, 600.0)
            )
        finally:
            slot.task = None

    def auto_commit_cards(self) -> None:
        """Periodically git-add+commit all changes to keep base repo clean."""
        now = time.time()
        if now - self._last_auto_commit < self._AUTO_COMMIT_INTERVAL:
            return
        self._last_auto_commit = now
        try:
            wd = self._workdir
            ok, stdout, _, _ = run_git(wd, ["git", "status", "--porcelain"])
            if not ok or not stdout.strip():
                return
            run_git(wd, ["git", "add", "-A"])
            run_git(wd, ["git", "commit", "-m", "chore: sync board state and project files"])
            log_event(self._log_path, "INFO", "auto-committed workspace state")
        except Exception as exc:
            log_event(self._log_path, "WARN", "auto-commit failed", error=str(exc))
