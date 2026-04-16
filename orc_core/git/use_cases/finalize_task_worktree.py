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
from ...git.git_dto import WorktreeSession
from ...tasks.dto import Task


class Integrator(Protocol):
    """Port for main-branch integration."""
    def integrate(self, session_id: str, task: Task, execution_workdir: str) -> bool: ...


def finalize_completed_worktree(
    card: CardView,
    worktree: WorktreeSession,
    slot,
    board: BoardGateway,
    integrator: Integrator,
    cleanup_fn,
    log_path: Path,
    main_branch: str,
    publisher,
    worktree_lock: threading.Lock,
) -> bool:
    """Integrate worktree into main and clean up. Returns True on success."""
    task_obj = slot.task or Task(task_id=card.id, text=card.title or card.id, done=True)
    integrated = integrator.integrate(slot.session_id, task_obj, worktree.worktree_path)
    if integrated:
        # Card must not reach STAGE_DONE before the squash merge lands. The
        # state machine keeps the card in STAGE_HANDOFF with action=DONE until
        # this point; promote it now, after code is on the main branch.
        if card.stage != STAGE_DONE:
            board.move_card(card, STAGE_DONE, reason="integrated into main")
            board.save_card(card)
        with worktree_lock:
            cleanup_fn(worktree, log_path)
        return True
    else:
        log_event(log_path, "WARN", "integration failed, keeping worktree",
                  task_id=card.id, worktree=worktree.worktree_path)
        publisher.emit("escalate", card.id,
                        f"{card.id} squash-merge to {main_branch} failed; "
                        f"card held in Handoff for retry")
        # Card is already in STAGE_HANDOFF (it never left). Reset action so
        # the next integrator pull picks it up again instead of treating it
        # as fully Done.
        card.action = Action.INTEGRATING
        board.save_card(card)
        return False
