#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker runner: executes kanban card assignments in agent threads."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from ...board.action_constants import Action
from ...config import OrcConfig
from ...tasks.completion.outcomes import TaskOutcomeTracker
from ...git.integration_manager import IntegrationManager
from ...git.git_helpers import attempt_autocommit_fallback, git_run, has_code_changes_ahead, has_commits_ahead_of_branch
from ...board.kanban_role_registry import ROLE_CODER, ROLE_INTEGRATOR, ROLE_REVIEWER, ROLE_TESTER
from ...board.stage_constants import STAGE_DONE
from ...tasks.status import TaskExecutionStatus
from ..infra.protocols import CompletionNotifier, EventPublisher, RunnerLifecycle, RunnerStateManager, WorkDistributor
from ...board.kanban_pull import WorkAssignment
from ..infra.agent_output import process_agent_result
from ..roles import build_prompt
from ...log import log_event
from ...quit_signal import is_quit_after_task_requested
from ...tasks.use_cases.process_task_result import (
    process_completed_task,
    handle_task_failure,
    escalate_if_threshold_reached,
)
from ...git.use_cases.finalize_task_worktree import finalize_completed_worktree
from ..session.types import SessionSlot, SlotStatus
from ..infra.protocols import TaskExecutor
from ...tasks.dto import Task
from ...git.git_dto import WorktreeSession
from ...git.worktree_flow import cleanup_task_worktree, create_task_worktree

_logger = logging.getLogger(__name__)
_DELIVERY_ROLES = frozenset({ROLE_CODER, ROLE_REVIEWER, ROLE_TESTER})


_DEFAULT_TOKENS_PER_EFFORT = 5000  # effort_score * this = default budget
_MIN_TOKEN_BUDGET = 20000  # guard against effort=0 / missing estimate


def _update_card_token_budget(card, board, log_path: Path) -> None:
    """Initialize or refresh the token budget for a card.

    - If effort_score > 0, budget = effort_score * _DEFAULT_TOKENS_PER_EFFORT.
    - If effort_score <= 0 (e.g. architect reset it for re-estimation), still
      set a minimum floor so the card can't burn tokens without any ceiling.
    - Re-applies when effort_score changed (architect re-estimated) and the
      current budget no longer matches the expected value for the new effort.
    """
    expected = card.effort_score * _DEFAULT_TOKENS_PER_EFFORT if card.effort_score > 0 else _MIN_TOKEN_BUDGET
    if card.token_budget == expected:
        return
    # Only grow the budget or install an initial value — never silently
    # shrink below what the card already used.
    if card.token_budget > 0 and expected < card.token_budget:
        return
    previous = card.token_budget
    card.token_budget = expected
    board.save_card(card)
    log_event(log_path, "INFO", "token budget updated",
              task_id=card.id, previous=previous,
              budget=card.token_budget, effort=card.effort_score)


def _accumulate_card_tokens(card, board, workdir: str, log_path: Path) -> None:
    """Read per-task token usage from stats file and update card.tokens_spent."""
    import json
    from ...infra.io.state_paths import stats_path
    stats_file = stats_path(workdir)
    if not stats_file.exists():
        return
    try:
        stats = json.loads(stats_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    tokens_by_task = stats.get("tokens_by_task", {})
    task_tokens = tokens_by_task.get(card.id, 0)
    if task_tokens and int(task_tokens) > card.tokens_spent:
        card.tokens_spent = int(task_tokens)
        board.save_card(card)


def _check_and_block_budget(card, board, publisher, log_path: Path) -> bool:
    """Block card if token budget is exhausted. Returns True if blocked."""
    if not card.is_budget_exhausted:
        return False
    reason = f"token budget exhausted: {card.tokens_spent}/{card.token_budget}"
    log_event(log_path, "WARN", "card blocked: token budget exhausted",
              task_id=card.id, tokens_spent=card.tokens_spent, token_budget=card.token_budget)
    publisher.emit("escalate", card.id, f"{card.id} BLOCKED: {reason}")
    card.block(reason)
    board.save_card(card)
    return True


def _verify_and_commit_uncommitted(
    workdir: str, main_branch: str, log_path: Path, task_id: str, task_text: str,
) -> None:
    """Autocommit any uncommitted source code left by the agent.

    This runs BEFORE the delivery check so that has_code_changes_ahead()
    sees committed changes and the code is preserved in the branch.
    """
    ok, porcelain, _, _ = git_run(
        workdir, log_path, ["git", "status", "--porcelain"], label="verify:uncommitted_check",
    )
    if not ok or not porcelain:
        return
    from ...git.git_helpers import parse_git_porcelain
    tracked, untracked = parse_git_porcelain(porcelain)
    code_dirty = [p for p in tracked + untracked
                  if not p.startswith("tasks/") and not p.startswith(".orc/")
                  and not p.startswith(".cursor/") and "__pycache__" not in p]
    if not code_dirty:
        return
    log_event(log_path, "WARN", "post-agent verification: uncommitted code found, autocommitting",
              task_id=task_id, count=len(code_dirty), sample=code_dirty[:5])
    attempt_autocommit_fallback(workdir, log_path, task_id, task_text)


def _gather_git_context(workdir: str, main_branch: str, log_path: Path) -> str:
    """Gather git log and diff stat from worktree to inject into agent prompt."""
    parts: list[str] = []
    ok_log, log_out, _, _ = git_run(
        workdir, log_path,
        ["git", "log", "--oneline", f"{main_branch}..HEAD", "--", ".", ":!tasks/"],
        label="git_context:log",
    )
    if ok_log and log_out.strip():
        parts.append(f"### Commits on this branch (vs {main_branch})\n```\n{log_out.strip()}\n```")

    ok_stat, stat_out, _, _ = git_run(
        workdir, log_path,
        ["git", "diff", "--stat", main_branch, "--", ".", ":!tasks/"],
        label="git_context:diff_stat",
    )
    if ok_stat and stat_out.strip():
        parts.append(f"### Changed files (vs {main_branch})\n```\n{stat_out.strip()}\n```")

    ok_status, status_out, _, _ = git_run(
        workdir, log_path,
        ["git", "status", "--short"],
        label="git_context:status",
    )
    if ok_status and status_out.strip():
        # Filter out tasks/ lines
        non_task = [l for l in status_out.strip().splitlines() if "tasks/" not in l]
        if non_task:
            parts.append(f"### Uncommitted changes\n```\n" + "\n".join(non_task) + "\n```")

    if not parts:
        return ""
    return "## Branch State (pre-gathered by orchestrator)\n\n" + "\n\n".join(parts)


class KanbanWorkerRunner:
    """Runs worker agent loops: pick task, execute, handle results."""

    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine: TaskExecutor,
        distributor: WorkDistributor,
        publisher: EventPublisher,
        config: OrcConfig,
        main_branch: str,
        slots_lock: threading.Lock,
        worktree_lock: threading.Lock,
        outcomes: TaskOutcomeTracker,
        lifecycle: RunnerLifecycle,
        notifier: CompletionNotifier,
        state_manager: RunnerStateManager,
        integrator: IntegrationManager,
    ) -> None:
        self._workdir = workdir
        self._log_path = log_path
        self._engine = engine
        self._distributor = distributor
        self._publisher = publisher
        self._config = config
        self._main_branch = main_branch
        self._slots_lock = slots_lock
        self._worktree_lock = worktree_lock
        self._outcomes = outcomes
        self._lifecycle = lifecycle
        self._notifier = notifier
        self._state_manager = state_manager
        self._integrator = integrator

    # ── Main loop ───────────────────────────────────────────────

    def run(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self._publisher.emit("system", "", f"{sid} worker started, scanning board...")
        try:
            idle_reason_logged: str = ""
            while self._lifecycle.should_continue(slot):
                self._distributor.refresh()
                assignment = self._distributor.pick_worker_task(sid)
                if assignment is None:
                    reason = self._distributor.diagnose_no_work()
                    if reason != idle_reason_logged:
                        self._publisher.emit("system", "", f"{sid} idle — {reason}")
                        idle_reason_logged = reason
                    self._lifecycle.sleep(2.0)
                    if not self._distributor.has_remaining_work():
                        self._publisher.emit("system", "", f"{sid} no remaining work, stopping")
                        break
                    continue
                idle_reason_logged = ""
                self.execute_assignment(slot, assignment)
                if is_quit_after_task_requested():
                    self._publisher.emit("system", "", f"{sid} finished task, exiting (quit-after-task)")
                    break
                self._lifecycle.sleep(1.0)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.mark_crashed(exc, traceback.format_exc())
            self._publisher.emit("escalate", "", f"{sid} CRASHED: {type(exc).__name__}: {exc}")
            log_event(self._log_path, "ERROR", "worker crashed",
                      session_id=sid, error=str(exc),
                      traceback=traceback.format_exc()[:2000])
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED

    # ── Assignment execution ────────────────────────────────────

    def execute_assignment(self, slot: SessionSlot, assignment: WorkAssignment) -> None:
        card, role, sid = assignment.card, assignment.role, slot.session_id
        self._publisher.log_assign(card.id, role, sid)
        log_event(self._log_path, "INFO", "executing",
                  session_id=sid, task_id=card.id, role=role, stage=card.stage)
        task_start = time.time()
        worktree: Optional[WorktreeSession] = None
        assignment_succeeded = False
        try:
            if assignment.needs_worktree:
                with self._worktree_lock:
                    worktree = create_task_worktree(
                        base_workdir=self._workdir, task_id=card.id,
                        log_path=self._log_path, main_branch=self._main_branch,
                    )
                wd = worktree.worktree_path
                if not worktree.reused:
                    self._publisher.emit("system", card.id, f"{card.id} worktree ready")
            else:
                wd = self._workdir
            git_context = _gather_git_context(wd, self._main_branch, self._log_path) if assignment.needs_worktree else ""
            # Re-read card from board to detect concurrent modifications
            # (e.g., teamlead blocked or moved the card while worktree was being created)
            fresh_card = self._distributor.board.card_by_id(card.id)
            if fresh_card is None or fresh_card.action == Action.BLOCKED:
                _logger.warning("Card %s was modified before agent launch (action=%s), aborting assignment",
                                card.id, fresh_card.action if fresh_card else "DELETED")
                log_event(self._log_path, "WARN", "assignment aborted: card state changed",
                          task_id=card.id, action=fresh_card.action if fresh_card else "deleted")
                return
            prompt = build_prompt(role, fresh_card, self._distributor.board, main_branch=self._main_branch, git_context=git_context)
            task = Task(task_id=card.id, text=card.title or card.id, done=False)
            slot.task = task
            self._publisher.emit("system", card.id, f"{card.id} launching {role} agent...")
            commit_phase = self._config.commit_phase and assignment.needs_worktree
            result = self._engine.execute(self._state_manager.make_request(task, prompt, wd, sid,
                                                              commit_phase, 1800.0))

            if result and result.status == TaskExecutionStatus.COMPLETED:
                # Post-agent verification: autocommit any uncommitted code
                # left by the agent before checking delivery.
                if assignment.needs_worktree and role in _DELIVERY_ROLES:
                    _verify_and_commit_uncommitted(
                        wd, self._main_branch, self._log_path, card.id, card.title or card.id,
                    )
                if (
                    assignment.needs_worktree
                    and role in _DELIVERY_ROLES
                    and not has_code_changes_ahead(wd, self._main_branch, self._log_path)
                ):
                    has_any = has_commits_ahead_of_branch(wd, self._main_branch, self._log_path)
                    reason = "no_code_changes_for_delivery_role"
                    self._publisher.emit(
                        "escalate",
                        card.id,
                        f"{card.id} {role} completed without code changes "
                        f"(card-only commits: {has_any}); retrying delivery cycle",
                    )
                    log_event(
                        self._log_path,
                        "WARN",
                        "delivery role finished without code changes ahead of main",
                        task_id=card.id,
                        role=role,
                        workdir=wd,
                        main_branch=self._main_branch,
                        card_only_commits=has_any,
                    )
                    handle_task_failure(card, reason, self._outcomes, self._publisher, role)
                    # Token accounting before escalation — agent burned tokens even
                    # without delivering code, we need that visible to budget checks.
                    _accumulate_card_tokens(card, self._distributor.board, self._workdir, self._log_path)
                    _update_card_token_budget(card, self._distributor.board, self._log_path)
                    _check_and_block_budget(card, self._distributor.board, self._publisher, self._log_path)
                    escalate_if_threshold_reached(
                        card, reason,
                        self._distributor.board, self._outcomes,
                        self._publisher, self._notifier, self._log_path,
                    )
                    return
                elapsed = time.time() - task_start
                from functools import partial
                result_processor = partial(process_agent_result, execution_workdir=wd, main_branch=self._main_branch) if assignment.needs_worktree else partial(process_agent_result, main_branch=self._main_branch)
                errors = process_completed_task(
                    board=self._distributor.board, card=card, role=role,
                    elapsed=elapsed, outcomes=self._outcomes,
                    publisher=self._publisher, notifier=self._notifier,
                    log_path=self._log_path,
                    agent_result_processor=result_processor,
                )
                # Token work AFTER process_completed_task so we don't overwrite
                # the agent's just-applied card edits with a stale `card` snapshot
                # taken before the agent ran.
                _accumulate_card_tokens(card, self._distributor.board, self._workdir, self._log_path)
                _update_card_token_budget(card, self._distributor.board, self._log_path)
                if _check_and_block_budget(card, self._distributor.board, self._publisher, self._log_path):
                    return
                if errors:
                    self._outcomes.record_failed(card.id)
                else:
                    assignment_succeeded = True
            else:
                # Failure path — agent did not modify the card body, so it's safe
                # to sync tokens/budget on the (unchanged) `card` snapshot now.
                _accumulate_card_tokens(card, self._distributor.board, self._workdir, self._log_path)
                _update_card_token_budget(card, self._distributor.board, self._log_path)
                if _check_and_block_budget(card, self._distributor.board, self._publisher, self._log_path):
                    return
                reason = result.reason if result else "no result"
                handle_task_failure(card, reason, self._outcomes, self._publisher, role)
                escalate_if_threshold_reached(
                    card, f"agent returned: {reason}",
                    self._distributor.board, self._outcomes,
                    self._publisher, self._notifier, self._log_path,
                )
        except Exception as exc:
            self._publisher.emit("escalate", card.id,
                                   f"{card.id} ERROR: {type(exc).__name__}: {exc}")
            log_event(self._log_path, "ERROR", "assignment failed",
                      task_id=card.id, error=str(exc))
            self._outcomes.record_failed(card.id)
            escalate_if_threshold_reached(
                card, f"{type(exc).__name__}: {exc}",
                self._distributor.board, self._outcomes,
                self._publisher, self._notifier, self._log_path,
            )
        else:
            # Reset failure counter only after true successful completion.
            if assignment_succeeded:
                self._outcomes.reset_fail_count(card.id)
        finally:
            if worktree:
                # Integrate worktree commits into main before cleanup.
                # Check action, not stage: the integrator sets action=Done but
                # the card stays in STAGE_HANDOFF until finalize succeeds.
                if card.action == Action.DONE:
                    finalize_completed_worktree(
                        card=card, worktree=worktree, slot=slot,
                        board=self._distributor.board, integrator=self._integrator,
                        cleanup_fn=cleanup_task_worktree, log_path=self._log_path,
                        main_branch=self._main_branch, publisher=self._publisher,
                        worktree_lock=self._worktree_lock,
                    )
                elif card.action == Action.BLOCKED:
                    # Blocked cards won't be picked up again — otherwise the
                    # worktree would leak forever (cleanup_done_worktrees only
                    # sweeps STAGE_DONE at startup).
                    try:
                        with self._worktree_lock:
                            cleanup_task_worktree(worktree, self._log_path)
                    except Exception as exc:
                        log_event(self._log_path, "WARN",
                                  "failed to clean worktree for blocked card",
                                  task_id=card.id, error=str(exc)[:200])
            slot.task = None
            self._distributor.release_card(card.id)
