#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead step strategies — each encapsulates one cohesive responsibility of the teamlead loop."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Protocol

from ...board.kanban_card import KanbanCard
from ...board.action_constants import Action
from ...board.use_cases.escalate_card import escalate_card
from ...log import log_event
from ...tasks.ports import GitIntegrationPort, StatePathsPort
from ...tasks.status import TaskExecutionStatus
from ...tasks.dto import Task
from ..session.types import SessionSlot
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
    active_tasks_provider: Callable[[], dict[str, str]] = field(default_factory=dict)
    known_sessions_provider: Callable[[], set[str]] = field(default_factory=set)

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
                notifier=self.notifier,
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
        escalate_card(self.distributor.board, card)
        self.outcomes.set_arbitrated_loop(card.id, card.loop_count)
        msg = (f"ESCALATION: Task {card.id} ({card.title}) blocked. "
               f"Loop count: {card.loop_count}. Stage: {card.stage}.")
        self.publisher.log_escalate(card.id, msg)
        self.notifier.notify_escalation(card.id, card.title, card.stage, card.loop_count)
        log_event(self.log_path, "WARN", "escalation", task_id=card.id, detail=msg)
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.CARD_ESCALATED,
            "loop_count_threshold",
            task_id=card.id,
            context={"loop_count": card.loop_count, "stage": card.stage,
                     "title": card.title[:80]},
        )


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
        # arbitrated_at_loop guards "same-loop bounceback" — a coder-loop
        # card that already got arbitrated at its current loop_count and
        # hasn't bounced further shouldn't be re-arbitrated until it loops
        # again. But cards in BLOCKED or ARBITRATION are a *different*
        # class of signal: budget exhaustion, integration failure,
        # escalation threshold, or an in-flight arbitration that never
        # landed a decision. Their loop_count is often 0 because the
        # block/arbitration happened off the loop path. Without this
        # exemption such a card (prev_arb >= loop_count) gets released
        # every teamlead tick without ever reaching a decision and
        # stays stuck — observed today on AUDIT-001-C and EMP-001 after
        # a mid-arbitration ORC restart left them in Action.ARBITRATION
        # with no agent, and the guard kept releasing them forever.
        if (
            card.action not in (Action.BLOCKED, Action.ARBITRATION)
            and card.loop_count <= prev_arb
        ):
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
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.TEAMLEAD_ARBITRATION,
            "loop_count_bounceback",
            task_id=card.id,
            context={"loop_count": card.loop_count,
                     "escalation_candidate": bool(needs_esc),
                     "stage": card.stage},
        )
        # Leaving Blocked → Arbitration must run the unblock cleanup so the
        # recovered card doesn't re-exhaust its budget on the very next
        # pick_best. unblock() strips accumulated `## Block Reason`
        # sections, resets loop_count/finalize_retries, offsets
        # tokens_discarded to cancel the historical budget debt, and
        # zeroes token_budget. It forces action=CODING as a side-effect,
        # which is why we re-assign to Action.ARBITRATION immediately
        # after — the downstream flow still needs the card in Arbitration
        # while the AI deliberates.
        if card.action == Action.BLOCKED:
            card.unblock()
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
        # Seed with current time so the first check fires after _BASE_INTERVAL,
        # not on the very first teamlead iteration. A fresh ORC start has no
        # work-attempt history, so detect_stuck_cards on ancient updated_at
        # timestamps would mis-flag backlog cards as stuck and burn a full
        # teamlead AI invocation on a spurious "deadlock" diagnostic.
        self._last_check: float = time.time()
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
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.TEAMLEAD_HEALTH_CHECK,
            diag_text.split("\n", 1)[0][:200] if diag_text else "board_deadlock",
            context={"consecutive": self._consecutive, "diagnostic": diag_text[:500]},
        )
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


class BlockedSweepStep:
    """Aggregate blocked cards into a single human-review Telegram alert.

    The per-card notify_escalation still fires when each card lands in
    Blocked, but batch escalations flood the channel. This sweep emits
    one message whenever the Blocked set changes and contains >1 card,
    and re-emits only when the set actually changes — not on every tick.
    """
    name = "blocked_sweep"
    _INTERVAL = 600.0
    _MIN_CARDS = 2

    def __init__(self) -> None:
        self._last_run: float = 0.0
        self._last_signature: tuple[str, ...] = ()

    def run(self, ctx: TeamleadContext, slot: SessionSlot, sid: str) -> None:
        now = time.time()
        if now - self._last_run < self._INTERVAL:
            return
        self._last_run = now
        blocked: list[tuple[str, str]] = [
            (card.id, card.stage)
            for card in ctx.distributor.board.cards
            if card.action == Action.BLOCKED and not card.is_done
        ]
        signature = tuple(sorted(card_id for card_id, _ in blocked))
        if len(blocked) < self._MIN_CARDS:
            self._last_signature = signature
            return
        if signature == self._last_signature:
            return
        self._last_signature = signature
        ctx.notifier.notify_blocked_accumulation(blocked)
        ctx.publisher.emit(
            "teamlead", "",
            f"Blocked sweep: {len(blocked)} card(s) awaiting human review",
        )
        log_event(
            ctx.log_path,
            "WARN",
            "teamlead blocked-sweep aggregated alert",
            session_id=sid,
            count=len(blocked),
            cards=[c for c, _ in blocked[:20]],
        )


class AutoCommitStep:
    """Periodically git-add+commit to keep the base repo clean."""
    name = "auto_commit"

    _INTERVAL = 120.0

    def __init__(self, git_integration: GitIntegrationPort) -> None:
        self._last_commit: float = 0.0
        self._git = git_integration

    def run(self, ctx: TeamleadContext, slot: Optional[SessionSlot] = None, sid: str = "") -> None:
        now = time.time()
        if now - self._last_commit < self._INTERVAL:
            return
        self._last_commit = now
        try:
            wd = ctx.workdir
            git = self._git
            ok_cherry, out_cherry, _, _ = git.run(wd, ["git", "rev-parse", "--git-path", "CHERRY_PICK_HEAD"])
            if ok_cherry:
                cherry_pick_head = (out_cherry or "").strip()
                if cherry_pick_head and Path(cherry_pick_head).exists():
                    log_event(ctx.log_path, "WARN", "auto-commit skipped: cherry-pick in progress",
                              path=cherry_pick_head)
                    return
            # Same guard for in-progress merges (MERGE_HEAD) and squashes
            # (SQUASH_MSG) — committing a dirty tree that still has
            # unresolved conflicts would write <<<<<<< markers straight
            # into main (jeeves 2026-04-20: MGR-001-A.md frontmatter).
            for marker in ("MERGE_HEAD", "SQUASH_MSG", "REBASE_HEAD"):
                ok_m, out_m, _, _ = git.run(wd, ["git", "rev-parse", "--git-path", marker])
                if ok_m:
                    marker_path = (out_m or "").strip()
                    if marker_path and Path(marker_path).exists():
                        log_event(ctx.log_path, "WARN", f"auto-commit skipped: {marker.lower()} present",
                                  path=marker_path)
                        return
            # Last line of defence: scan the working tree for unresolved
            # conflict files regardless of git's internal state. A merge
            # expert that wrote a bogus commit (see conflict_resolver
            # defence) or a stray manual edit could leave conflict
            # markers without any of the in-progress marker files.
            ok_u, unresolved, _, _ = git.run(wd, ["git", "diff", "--name-only", "--diff-filter=U"])
            if ok_u and (unresolved or "").strip():
                log_event(ctx.log_path, "WARN", "auto-commit skipped: unresolved conflict files present",
                          files=unresolved.strip().splitlines()[:20])
                return
            ok, stdout, _, _ = git.run(wd, ["git", "status", "--porcelain"])
            if not ok or not stdout.strip():
                return
            changed_paths = [line[3:].strip() for line in stdout.splitlines() if len(line) >= 4]
            task_paths = [p for p in changed_paths if p.startswith("tasks/")]
            other_paths = [
                p for p in changed_paths
                if not p.startswith("tasks/") and not git.is_runtime_artifact(p)
            ]
            if task_paths:
                for tp in task_paths:
                    git.run(wd, ["git", "add", "--", tp])
                self._commit_or_amend(wd, git, ctx, git.board_commit_message())
                log_event(ctx.log_path, "INFO", "auto-committed board state",
                          task_paths=task_paths[:20])
            if other_paths:
                # Stage paths explicitly — `git add -A` would also sweep up
                # runtime artifacts (.orc/, .cursor/, __pycache__) and any
                # accidentally-untracked secrets.
                for op in other_paths:
                    git.run(wd, ["git", "add", "--", op])
                self._commit_or_amend(wd, git, ctx, git.sync_commit_message())
                log_event(ctx.log_path, "INFO", "auto-committed workspace state",
                          paths=other_paths[:20])
        except Exception as exc:
            log_event(ctx.log_path, "WARN", "auto-commit failed", error=str(exc))

    @staticmethod
    def _commit_or_amend(wd: str, git: GitIntegrationPort, ctx: TeamleadContext, message: str) -> None:
        """Amend consecutive unpushed auto-commits into one rolling commit.

        Every card-state tick (tokens_spent bump, state_version bump,
        stage/action move) used to produce its own "chore(board):..."
        commit on the 2-minute AutoCommit cadence. Across a 2-hour
        session that piled up 40+ chore commits per 5 feats, burying
        the real feature commits in noise on master.

        If HEAD already carries one of the two auto-commit messages we
        emit AND the commit has not yet been pushed to the upstream
        branch, fold the new changes into HEAD via `commit --amend`
        instead of creating a fresh commit. Once a real commit lands
        between auto-commit runs (a feat integrator commit, a manual
        commit, anything not matching our own auto-commit patterns),
        the next auto-commit starts a fresh rolling chore.

        The "not yet pushed" guard is essential: amending a pushed
        commit would require force-push, which we never do. We detect
        this by checking `git rev-list @{upstream}..HEAD` — if it is
        empty, HEAD has already been shared and must be preserved
        as-is. If there is no upstream configured at all, default to
        fresh commits (safer).
        """
        auto_commit_messages = (git.board_commit_message(), git.sync_commit_message())
        amend_ok = False
        ok_msg, head_msg, _, _ = git.run(wd, ["git", "log", "-1", "--format=%s"])
        if ok_msg and (head_msg or "").strip() in auto_commit_messages:
            ok_ahead, ahead_list, _, _ = git.run(wd, ["git", "rev-list", "@{upstream}..HEAD"])
            if ok_ahead and (ahead_list or "").strip():
                amend_ok = True
        if amend_ok:
            git.run(wd, ["git", "commit", "--amend", "--no-edit"])
        else:
            git.run(wd, ["git", "commit", "-m", message])
