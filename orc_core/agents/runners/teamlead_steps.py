#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead step strategies — each encapsulates one cohesive responsibility of the teamlead loop."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

from ...board.kanban_card import KanbanCard
from ...board.action_constants import Action
from ...log import log_event
from ...tasks.ports import StatePathsPort
from ...tasks.status import TaskExecutionStatus
from ...tasks.dto import Task
from ..session.types import SessionSlot
from ...git.git_helpers import run_git
from ..infra.protocols import (
    EventPublisher, RunnerLifecycle, RunnerNotifier, RunnerStateManager,
    TaskExecutor, WorkDistributor,
)
from ..roles import build_teamlead_prompt
from .arbitration_outcomes import ARBITRATION_OUTCOMES
from .teamlead_autounblock import release_stale_assignments, resolve_cycle_with_decomposition
from .teamlead_actions import execute_teamlead_actions, parse_teamlead_decision
from .teamlead_stats import find_latest_agent_log, load_token_stats

if TYPE_CHECKING:
    from ...tasks.completion.outcomes import TaskOutcomeTracker


@dataclass
class TeamleadContext:
    """Shared collaborators used by each teamlead step."""
    workdir: str
    log_path: Path
    engine: TaskExecutor
    distributor: WorkDistributor
    publisher: EventPublisher
    lifecycle: RunnerLifecycle
    notifier: RunnerNotifier
    state_manager: RunnerStateManager
    outcomes: "TaskOutcomeTracker"
    state_paths: StatePathsPort

    def decision_path(self) -> Path:
        p = Path(self.workdir) / ".orc"
        p.mkdir(parents=True, exist_ok=True)
        return p / "teamlead-decision.md"

    def invoke_teamlead(self, slot: SessionSlot, sid: str, task: Task, prompt: str):
        slot.task = task
        try:
            return self.engine.execute(
                self.state_manager.make_request(task, prompt, self.workdir, sid, False, 600.0)
            )
        finally:
            slot.task = None

    def process_decision(self, dec_path: Path) -> None:
        if not dec_path.exists():
            _logger.warning("Teamlead decision file not found: %s — agent may have written to wrong path", dec_path)
            log_event(self.log_path, "WARN", "teamlead decision file not found",
                      path=str(dec_path))
            return
        try:
            decision = parse_teamlead_decision(dec_path)
            errors = execute_teamlead_actions(
                self.distributor.board, decision, self.publisher, self.log_path,
            )
            if errors:
                for e in errors:
                    self.publisher.emit("escalate", "", f"[TL] Action failed: {e}")
        except Exception as exc:
            self.publisher.emit("escalate", "", f"[TL] Decision parse failed: {exc}")
            log_event(self.log_path, "WARN", "teamlead decision parse failed", error=str(exc))
        finally:
            try:
                dec_path.unlink(missing_ok=True)
            except OSError:
                pass

    def escalate(self, card: KanbanCard) -> None:
        card.block()
        self.distributor.board.save_card(card)
        self.outcomes.set_arbitrated_loop(card.id, card.loop_count)
        msg = (f"ESCALATION: Task {card.id} ({card.title}) blocked. "
               f"Loop count: {card.loop_count}. Stage: {card.stage}.")
        self.publisher.log_escalate(card.id, msg)
        self.notifier.send_telegram(
            f"\U0001f6a8 {card.id} BLOCKED\n"
            f"  {card.title}\n"
            f"  Stage: {card.stage}, loops: {card.loop_count}\n"
            f"  Use /unblock {card.id} <directive> to resume"
        )
        log_event(self.log_path, "WARN", "escalation", task_id=card.id, detail=msg)


class TeamleadStep(Protocol):
    """Port for a single step in the teamlead loop."""
    name: str
    def run(self, ctx: TeamleadContext, slot: SessionSlot, sid: str) -> None: ...


class ArbitrationStep:
    """Handle looping/blocked cards via arbitration-mode teamlead agent."""
    name = "arbitration"
    _REPEAT_COOLDOWN_SECONDS = 45.0

    def __init__(self) -> None:
        self._last_attempt: dict[str, tuple[tuple[str, str, str, int], float]] = {}

    def run(self, ctx: TeamleadContext, slot: SessionSlot, sid: str) -> None:
        card = ctx.distributor.pick_teamlead_task(sid)
        if card is None:
            return
        now = time.time()
        state_fp = (card.id, card.stage, card.action, card.loop_count)
        prev_attempt = self._last_attempt.get(card.id)
        if prev_attempt and prev_attempt[0] == state_fp and (now - prev_attempt[1]) < self._REPEAT_COOLDOWN_SECONDS:
            ctx.distributor.release_card(card.id)
            return
        self._last_attempt[card.id] = (state_fp, now)
        prev_arb = ctx.outcomes.get_arbitrated_loop(card.id)
        if card.loop_count <= prev_arb:
            ctx.distributor.release_card(card.id)
            return
        needs_esc = ctx.distributor.needs_escalation(card)
        if needs_esc:
            ctx.publisher.emit("escalate", card.id,
                               f"{card.id} loop_count={card.loop_count}, "
                               f"teamlead arbitrating before escalation")
        log_event(ctx.log_path, "INFO", "teamlead arbitration",
                  session_id=sid, task_id=card.id, loop_count=card.loop_count,
                  escalation_candidate=needs_esc)
        card.action = Action.ARBITRATION
        ctx.distributor.board.save_card(card)
        dec_path = ctx.decision_path()
        agent_log = find_latest_agent_log(ctx.workdir, card.id, paths=ctx.state_paths)
        prompt = build_teamlead_prompt(
            mode="arbitration", board=ctx.distributor.board, card=card,
            decision_path=str(dec_path), agent_log_path=agent_log,
            token_stats=load_token_stats(ctx.workdir, paths=ctx.state_paths),
        )
        task = Task(task_id=card.id, text=f"[TL] {card.title}", done=False)
        try:
            result = ctx.invoke_teamlead(slot, sid, task, prompt)
            if result and result.status == TaskExecutionStatus.COMPLETED:
                ctx.process_decision(dec_path)
                ctx.distributor.refresh()
                refreshed = ctx.distributor.board.card_by_id(card.id)
                if refreshed:
                    matched = False
                    for outcome in ARBITRATION_OUTCOMES:
                        if outcome.matches(refreshed, needs_esc):
                            outcome.apply(ctx, card, refreshed, needs_esc)
                            matched = True
                            break
                    # Fallback: if TL didn't produce a decision and card is
                    # still in Arbitration, return it to Coding so it doesn't
                    # burn tokens in an infinite arbitration loop.
                    if not matched and refreshed.action == Action.ARBITRATION:
                        refreshed.action = Action.CODING
                        ctx.distributor.board.save_card(refreshed)
                        ctx.publisher.emit("system", card.id,
                                           f"{card.id} arbitration produced no decision — "
                                           f"returning to Coding")
                        log_event(ctx.log_path, "WARN",
                                  "arbitration fallback: no decision file, returning to Coding",
                                  task_id=card.id, loop_count=card.loop_count)
        finally:
            ctx.distributor.release_card(card.id)
        ctx.lifecycle.sleep(3.0)


class DirectiveStep:
    """Run the teamlead agent to process a user directive."""
    name = "directive"

    def run_with_text(self, ctx: TeamleadContext, slot: SessionSlot, sid: str, directive_text: str) -> None:
        ctx.publisher.emit("directive", "", f"Teamlead processing: {directive_text}")
        log_event(ctx.log_path, "INFO", "teamlead directive start",
                  session_id=sid, directive=directive_text[:200])
        dec_path = ctx.decision_path()
        prompt = build_teamlead_prompt(
            mode="directive", board=ctx.distributor.board,
            directive_text=directive_text, decision_path=str(dec_path),
            token_stats=load_token_stats(ctx.workdir, paths=ctx.state_paths),
        )
        task = Task(task_id="tl-directive", text=f"[TL] {directive_text[:40]}", done=False)
        ctx.invoke_teamlead(slot, sid, task, prompt)
        ctx.process_decision(dec_path)
        ctx.lifecycle.sleep(2.0)

    def run(self, ctx: TeamleadContext, slot: SessionSlot, sid: str) -> None:  # Protocol default
        raise NotImplementedError("Use run_with_text — directive is pulled from DirectiveSource in the runner")


class HealthCheckStep:
    """Periodic board health diagnostic. Invokes agent only when a new issue is seen."""
    name = "health_check"

    _BASE_INTERVAL = 300.0
    _MAX_INTERVAL = 1800.0

    def __init__(self) -> None:
        self._last_check: float = 0.0
        self._consecutive: int = 0
        self._last_diagnostic: str = ""

    def due(self) -> bool:
        interval = min(self._BASE_INTERVAL * (2 ** self._consecutive), self._MAX_INTERVAL)
        return time.time() - self._last_check >= interval

    def run(self, ctx: TeamleadContext, slot: SessionSlot, sid: str) -> bool:  # type: ignore[override]
        """Returns True if a problem was found and the agent was invoked."""
        from ...board.use_cases.check_board_health import diagnose_board_health, should_skip_repeated_diagnostic

        self._last_check = time.time()
        diagnostic = diagnose_board_health(ctx.distributor.board, ctx.distributor)
        if diagnostic is None:
            self._consecutive = 0
            self._last_diagnostic = ""
            return False
        if diagnostic.is_dependency_only_starvation:
            log_event(ctx.log_path, "INFO", "health check: dep-only starvation, skipping AI",
                      session_id=sid)
            return False
        if diagnostic.has_cycle and resolve_cycle_with_decomposition(ctx, diagnostic):
            self._last_diagnostic = diagnostic.summary
            self._consecutive += 1
            return True
        if should_skip_repeated_diagnostic(diagnostic, self._last_diagnostic, self._consecutive):
            self._consecutive += 1
            log_event(ctx.log_path, "INFO",
                      "health check: same diagnostic as last time, skipping AI",
                      session_id=sid, consecutive=self._consecutive)
            return False
        self._last_diagnostic = diagnostic.summary
        self._consecutive += 1
        diag_text = diagnostic.summary
        ctx.publisher.emit("escalate", "", f"[TL] Health check: {diag_text.strip()}")
        log_event(ctx.log_path, "WARN", "board health issue detected",
                  session_id=sid, diagnostic=diag_text[:500])
        dec_path = ctx.decision_path()
        prompt = build_teamlead_prompt(
            mode="health", board=ctx.distributor.board,
            diagnostic_info=diag_text, decision_path=str(dec_path),
            token_stats=load_token_stats(ctx.workdir, paths=ctx.state_paths),
        )
        task = Task(task_id="tl-health", text="[TL] Board health check", done=False)
        ctx.invoke_teamlead(slot, sid, task, prompt)
        ctx.process_decision(dec_path)
        ctx.lifecycle.sleep(3.0)
        return True


class AutoUnblockStep:
    """Periodic deterministic unblock actions that do not require LLM arbitration."""
    name = "auto_unblock"
    _INTERVAL = 60.0

    def __init__(self) -> None:
        self._last_run: float = 0.0
        self._suspect_counts: dict[str, int] = {}

    def run(self, ctx: TeamleadContext, slot: SessionSlot, sid: str) -> None:
        now = time.time()
        if now - self._last_run < self._INTERVAL:
            return
        self._last_run = now
        released = release_stale_assignments(ctx, self._suspect_counts)
        if released:
            ctx.publisher.emit("teamlead", "", f"Auto-unblock released stale assignments: {released}")
            log_event(ctx.log_path, "WARN", "teamlead auto-unblock released stale assignments",
                      session_id=sid, released=released)


class AutoCommitStep:
    """Periodically git-add+commit to keep the base repo clean."""
    name = "auto_commit"

    _INTERVAL = 120.0

    def __init__(self) -> None:
        self._last_commit: float = 0.0

    def run(self, ctx: TeamleadContext, slot: Optional[SessionSlot] = None, sid: str = "") -> None:
        now = time.time()
        if now - self._last_commit < self._INTERVAL:
            return
        self._last_commit = now
        try:
            wd = ctx.workdir
            ok_cherry, out_cherry, _, _ = run_git(wd, ["git", "rev-parse", "--git-path", "CHERRY_PICK_HEAD"])
            if ok_cherry:
                cherry_pick_head = (out_cherry or "").strip()
                if cherry_pick_head and Path(cherry_pick_head).exists():
                    log_event(ctx.log_path, "WARN", "auto-commit skipped: cherry-pick in progress",
                              path=cherry_pick_head)
                    return
            ok, stdout, _, _ = run_git(wd, ["git", "status", "--porcelain"])
            if not ok or not stdout.strip():
                return
            from ...git.git_helpers import (
                is_runtime_artifact, sync_commit_message, board_commit_message,
            )
            changed_paths = [line[3:].strip() for line in stdout.splitlines() if len(line) >= 4]
            task_paths = [p for p in changed_paths if p.startswith("tasks/")]
            other_paths = [
                p for p in changed_paths
                if not p.startswith("tasks/") and not is_runtime_artifact(p)
            ]
            if task_paths:
                for tp in task_paths:
                    run_git(wd, ["git", "add", "--", tp])
                run_git(wd, ["git", "commit", "-m", board_commit_message()])
                log_event(ctx.log_path, "INFO", "auto-committed board state",
                          task_paths=task_paths[:20])
            if other_paths:
                # Stage paths explicitly — `git add -A` would also sweep up
                # runtime artifacts (.orc/, .cursor/, __pycache__) and any
                # accidentally-untracked secrets.
                for op in other_paths:
                    run_git(wd, ["git", "add", "--", op])
                run_git(wd, ["git", "commit", "-m", sync_commit_message()])
                log_event(ctx.log_path, "INFO", "auto-committed workspace state",
                          paths=other_paths[:20])
        except Exception as exc:
            log_event(ctx.log_path, "WARN", "auto-commit failed", error=str(exc))
