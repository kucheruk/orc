#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execution of a single kanban worker assignment."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from ...board.action_constants import Action
from ...board.kanban_role_registry import is_delivery_role
from ...git.git_dto import WorktreeSession
from ...git.git_helpers import has_code_changes_ahead, has_commits_ahead_of_branch
from ...git.use_cases.finalize_task_worktree import finalize_completed_worktree
from ...git.worktree_lifecycle import cleanup_task_worktree, create_task_worktree
from ...log import log_event
from ...tasks.dto import Task
from ...tasks.ports import GitIntegrationPort
from ...tasks.status import TaskExecutionStatus
from ...tasks.use_cases.process_task_result import (
    escalate_if_threshold_reached,
    handle_task_failure,
    process_completed_task,
)
from ..results.io import RESULT_TAG_ENV
from ..results.worker_result_processor import process_worker_card_result
from .worker_support import (
    accumulate_card_tokens,
    card_state_fingerprint,
    check_and_block_budget,
    gather_git_context,
    update_card_token_budget,
    verify_and_commit_uncommitted,
)

class WorkerAssignmentExecutor:
    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine,
        distributor,
        publisher,
        config,
        main_branch: str,
        worktree_lock,
        outcomes,
        notifier,
        state_manager,
        integrator,
        git_integration: GitIntegrationPort,
    ) -> None:
        self._workdir = workdir
        self._log_path = log_path
        self._engine = engine
        self._distributor = distributor
        self._publisher = publisher
        self._config = config
        self._main_branch = main_branch
        self._worktree_lock = worktree_lock
        self._outcomes = outcomes
        self._notifier = notifier
        self._state_manager = state_manager
        self._integrator = integrator
        self._git = git_integration

    def execute(self, slot, assignment, *, prompt_builder) -> None:
        card, role, sid = assignment.card, assignment.role, slot.session_id
        self._publisher.log_assign(card.id, role, sid)
        log_event(self._log_path, "INFO", "executing", session_id=sid, task_id=card.id, role=role, stage=card.stage)
        task_start = time.time()
        worktree: Optional[WorktreeSession] = None
        assignment_succeeded = False
        try:
            workdir = self._prepare_workdir(card.id, assignment.needs_worktree)
            worktree = workdir[1]
            wd = workdir[0]
            fresh_card = self._distributor.board.card_by_id(card.id)
            if fresh_card is None or fresh_card.action == Action.BLOCKED:
                return
            # Pre-launch budget check closes the race between `pick_best`
            # filtering and another attempt accumulating tokens past the
            # limit. Without this an exhausted card can be launched again
            # between pick and engine.execute.
            self._sync_tokens_and_budget(fresh_card)
            if check_and_block_budget(
                fresh_card, self._distributor.board, self._publisher, self._log_path, self._notifier,
            ):
                return
            pre_attempt_tokens = int(getattr(fresh_card, "tokens_spent", 0) or 0)
            launch_state = card_state_fingerprint(fresh_card)
            git_context = gather_git_context(wd, self._main_branch, self._log_path, git=self._git) if assignment.needs_worktree else ""
            prompt = prompt_builder(role, fresh_card, self._distributor.board, main_branch=self._main_branch, git_context=git_context)
            task = Task(task_id=card.id, text=card.title or card.id, done=False)
            slot.task = task
            self._publisher.emit("system", card.id, f"{card.id} launching {role} agent...")
            request = self._state_manager.make_request(
                task,
                prompt,
                wd,
                sid,
                self._config.commit_phase and assignment.needs_worktree,
                1800.0,
                {RESULT_TAG_ENV: fresh_card.stage},
            )
            result = self._engine.execute(request)
            if result and result.status == TaskExecutionStatus.COMPLETED:
                if self._discard_if_stale(card.id, launch_state):
                    self._mark_attempt_discarded(card.id, pre_attempt_tokens, reason="stale_fingerprint")
                    return
                if assignment.needs_worktree and is_delivery_role(role):
                    verify_and_commit_uncommitted(wd, self._main_branch, self._log_path, card.id, card.title or card.id, git=self._git)
                if self._reject_empty_delivery(card, role, assignment.needs_worktree, wd):
                    self._mark_attempt_discarded(card.id, pre_attempt_tokens, reason="empty_delivery")
                    return
                errors = process_completed_task(
                    board=self._distributor.board,
                    card=card,
                    role=role,
                    elapsed=time.time() - task_start,
                    outcomes=self._outcomes,
                    publisher=self._publisher,
                    notifier=self._notifier,
                    log_path=self._log_path,
                    agent_result_processor=lambda board, target, target_role: process_worker_card_result(
                        board,
                        target,
                        target_role,
                        agent_result_file=result.agent_result_file,
                        agent_run_id=result.agent_run_id,
                        outcomes=self._outcomes,
                    ),
                )
                self._sync_tokens_and_budget(card)
                if errors:
                    self._mark_attempt_discarded(card.id, pre_attempt_tokens, reason="validation_failed")
                if check_and_block_budget(card, self._distributor.board, self._publisher, self._log_path, self._notifier):
                    return
                if not errors:
                    assignment_succeeded = True
            else:
                self._mark_attempt_discarded(card.id, pre_attempt_tokens, reason="exec_not_completed")
                self._handle_failed_result(card, role, result.reason if result else "no result")
        except Exception as exc:
            self._publisher.emit("escalate", card.id, f"{card.id} ERROR: {type(exc).__name__}: {exc}")
            log_event(self._log_path, "ERROR", "assignment failed", task_id=card.id, error=str(exc))
            self._outcomes.record_failed(card.id)
            escalate_if_threshold_reached(
                card,
                f"{type(exc).__name__}: {exc}",
                self._distributor.board,
                self._outcomes,
                self._publisher,
                self._notifier,
                self._log_path,
            )
        else:
            if assignment_succeeded:
                self._outcomes.reset_fail_count(card.id)
        finally:
            self._cleanup_after_assignment(card, slot, worktree)

    def _prepare_workdir(self, card_id: str, needs_worktree: bool) -> tuple[str, Optional[WorktreeSession]]:
        if not needs_worktree:
            return self._workdir, None
        with self._worktree_lock:
            worktree = create_task_worktree(
                base_workdir=self._workdir,
                task_id=card_id,
                log_path=self._log_path,
                main_branch=self._main_branch,
            )
        if not worktree.reused:
            self._publisher.emit("system", card_id, f"{card_id} worktree ready")
        return worktree.worktree_path, worktree

    def _discard_if_stale(self, card_id: str, launch_state: tuple[str, str, str]) -> bool:
        latest_card = self._distributor.board.card_by_id(card_id)
        if latest_card is not None and card_state_fingerprint(latest_card) == launch_state:
            return False
        token_card = latest_card if latest_card is not None else self._distributor.board.card_by_id(card_id)
        if token_card is not None:
            self._sync_tokens_and_budget(token_card)
            check_and_block_budget(token_card, self._distributor.board, self._publisher, self._log_path, self._notifier)
        return True

    def _mark_attempt_discarded(self, card_id: str, pre_attempt_tokens: int, *, reason: str) -> None:
        card = self._distributor.board.card_by_id(card_id)
        if card is None:
            return
        self._sync_tokens_and_budget(card)
        attempt_tokens = max(0, int(getattr(card, "tokens_spent", 0) or 0) - int(pre_attempt_tokens))
        if attempt_tokens <= 0:
            return
        card.tokens_discarded = int(getattr(card, "tokens_discarded", 0) or 0) + attempt_tokens
        self._distributor.board.save_card(card)
        log_event(
            self._log_path,
            "INFO",
            "attempt tokens marked discarded",
            task_id=card.id,
            attempt_tokens=attempt_tokens,
            tokens_discarded=card.tokens_discarded,
            tokens_spent=card.tokens_spent,
            reason=reason,
        )
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.ATTEMPT_DISCARDED,
            reason,
            task_id=card.id,
            context={
                "tokens": attempt_tokens,
                "tokens_discarded": card.tokens_discarded,
                "tokens_spent": card.tokens_spent,
                "stage": card.stage,
            },
        )

    def _reject_empty_delivery(self, card, role: str, needs_worktree: bool, workdir: str) -> bool:
        if not needs_worktree or not is_delivery_role(role):
            return False
        if has_code_changes_ahead(workdir, self._main_branch, self._log_path):
            return False
        reason = "no_code_changes_for_delivery_role"
        has_any = has_commits_ahead_of_branch(workdir, self._main_branch, self._log_path)
        self._publisher.emit(
            "escalate",
            card.id,
            f"{card.id} {role} completed without code changes (card-only commits: {has_any}); retrying delivery cycle",
        )
        log_event(self._log_path, "WARN", "delivery role finished without code changes ahead of main", task_id=card.id, role=role)
        handle_task_failure(card, reason, self._outcomes, self._publisher, role)
        self._sync_tokens_and_budget(card)
        check_and_block_budget(card, self._distributor.board, self._publisher, self._log_path, self._notifier)
        escalate_if_threshold_reached(
            card,
            reason,
            self._distributor.board,
            self._outcomes,
            self._publisher,
            self._notifier,
            self._log_path,
        )
        return True

    def _handle_failed_result(self, card, role: str, reason: str) -> None:
        self._sync_tokens_and_budget(card)
        if check_and_block_budget(card, self._distributor.board, self._publisher, self._log_path, self._notifier):
            return
        handle_task_failure(card, reason, self._outcomes, self._publisher, role)
        escalate_if_threshold_reached(
            card,
            f"agent returned: {reason}",
            self._distributor.board,
            self._outcomes,
            self._publisher,
            self._notifier,
            self._log_path,
        )

    def _sync_tokens_and_budget(self, card) -> None:
        accumulate_card_tokens(card, self._distributor.board, self._workdir)
        update_card_token_budget(card, self._distributor.board, self._log_path)

    def _cleanup_after_assignment(self, card, slot, worktree: Optional[WorktreeSession]) -> None:
        # Finalize Handoff+Done regardless of whether the WorktreeSession
        # handle survived. An ORC restart between agent decision and cleanup
        # used to drop the session handle and strand the card in Handoff+Done
        # forever; now the squash-merge runs off the deterministic branch
        # name (orc/<card_id>) from the main workdir.
        #
        # Re-fetch from the board: apply_card_update_result mutates the card
        # returned by board.card_by_id(card.id), then calls board.refresh()
        # which does self._cards[:] = fresh_instances — that swaps the
        # in-memory list out from under us, so the `card` reference we
        # received from the assignment becomes a detached stale instance
        # still showing the pre-attempt action (Integrating). Without this
        # re-fetch the integrator's "done" transition never triggered
        # finalize_completed_worktree, so the squash-merge into master
        # was silently skipped and the card sat at Handoff+Done with its
        # branch still unmerged.
        fresh = self._distributor.board.card_by_id(card.id)
        if fresh is not None:
            card = fresh
        if card.action == Action.DONE:
            finalize_completed_worktree(
                card=card,
                worktree=worktree,
                slot=slot,
                board=self._distributor.board,
                integrator=self._integrator,
                cleanup_fn=cleanup_task_worktree,
                log_path=self._log_path,
                main_branch=self._main_branch,
                publisher=self._publisher,
                worktree_lock=self._worktree_lock,
            )
        elif worktree and card.action == Action.BLOCKED:
            with self._worktree_lock:
                cleanup_task_worktree(worktree, self._log_path)
        slot.task = None
        self._distributor.release_card(card.id)
