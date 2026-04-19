#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: finalize a completed task's worktree.

Integrates worktree commits into main branch, cleans up worktree on success,
or moves card back to Handoff on integration failure.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Protocol

from ...board.action_constants import Action
from ...board.gateway import BoardGateway, CardView
from ...board.stage_constants import STAGE_DONE, STAGE_HANDOFF
from ...log import log_event
from ...git.branch_resolver import task_branch_name
from ...git.git_dto import WorktreeSession
from ...tasks.dto import Task


class Integrator(Protocol):
    """Port for main-branch integration."""
    def integrate(
        self,
        session_id: str,
        task: Task,
        execution_workdir: str,
        *,
        branch_name: str = "",
    ) -> bool: ...


# Cap on consecutive failed squash-merge attempts before the card is
# parked in BLOCKED for a human (or teamlead) to resolve. Without a cap
# a permanent conflict would spin the integrator→finalize→fail loop
# indefinitely, burning tokens on every integrator re-approval.
MAX_FINALIZE_RETRIES = 3


def finalize_completed_worktree(
    card: CardView,
    worktree: WorktreeSession | None,
    slot,
    board: BoardGateway,
    integrator: Integrator,
    cleanup_fn,
    log_path: Path,
    main_branch: str,
    publisher,
    worktree_lock: threading.Lock,
) -> bool:
    """Integrate a task branch into main and clean up. Returns True on success.

    ``worktree`` may be None when the WorktreeSession handle was lost — e.g.
    after an ORC restart between the agent writing ``action=Done`` and
    ``_cleanup_after_assignment`` running. In that case the branch name is
    reconstructed from the card id and the merge proceeds from the main
    workdir alone; worktree cleanup is skipped because there is no session
    handle to clean up.
    """
    session_id = getattr(slot, "session_id", "") if slot is not None else ""
    task_obj: Task
    if slot is not None and getattr(slot, "task", None) is not None:
        task_obj = slot.task
    else:
        task_obj = Task(task_id=card.id, text=card.title or card.id, done=True)
    execution_workdir = worktree.worktree_path if worktree else ""
    # Fallback must mirror what worktree_lifecycle.create_task_worktree uses:
    # task_branch_name applies _safe_name (sanitizes /, spaces, truncates to 64)
    # so card IDs with special characters still resolve to the real branch.
    branch_name = worktree.branch_name if (worktree and worktree.branch_name) else task_branch_name(card.id)
    integrated = integrator.integrate(
        session_id, task_obj, execution_workdir, branch_name=branch_name,
    )
    if integrated:
        # Card must not reach STAGE_DONE before the squash merge lands. The
        # state machine keeps the card in STAGE_HANDOFF with action=DONE until
        # this point; promote it now, after code is on the main branch.
        if card.stage != STAGE_DONE:
            board.move_card(card, STAGE_DONE, reason="integrated into main")
            board.save_card(card)
        if worktree is not None:
            with worktree_lock:
                cleanup_fn(worktree, log_path)
        return True
    else:
        retries = int(getattr(card, "finalize_retries", 0) or 0) + 1
        card.finalize_retries = retries
        log_event(log_path, "WARN", "integration failed, keeping worktree",
                  task_id=card.id, worktree=execution_workdir, branch=branch_name,
                  finalize_retries=retries, cap=MAX_FINALIZE_RETRIES)
        if retries >= MAX_FINALIZE_RETRIES:
            # Permanent-looking failure: stop the retry loop and hand the
            # card off to a human / teamlead. BLOCKED prevents the
            # integrator from pulling it again; card.unblock() resets
            # finalize_retries so the next cycle starts fresh.
            card.block(
                reason=(
                    f"squash-merge to {main_branch} failed "
                    f"{retries}/{MAX_FINALIZE_RETRIES} times; needs human review"
                )
            )
            publisher.emit("escalate", card.id,
                           f"{card.id} squash-merge to {main_branch} failed "
                           f"{retries} times; parked in BLOCKED for review")
            board.save_card(card)
            return False
        publisher.emit("escalate", card.id,
                        f"{card.id} squash-merge to {main_branch} failed "
                        f"({retries}/{MAX_FINALIZE_RETRIES}); held in Handoff for retry")
        # Card is already in STAGE_HANDOFF (it never left). Reset action so
        # the next integrator pull picks it up again instead of treating it
        # as fully Done.
        card.action = Action.INTEGRATING
        board.save_card(card)
        return False
