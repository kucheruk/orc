#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull system: right-to-left scan to find the highest-priority work for a free worker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .kanban_constants import (
    STAGE_CODING,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_INBOX,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_TODO,
    Action,
)

_pull_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard
    from .kanban_card import KanbanCard

from .kanban_role_registry import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TESTER,
)


@dataclass(frozen=True)
class WorkAssignment:
    card: "KanbanCard"
    role: str
    needs_worktree: bool


def find_next_work(board: "KanbanBoard") -> Optional[WorkAssignment]:
    """Scan the board right-to-left and return the best available assignment.

    Returns None if no work is available (all columns empty or WIP-blocked).
    """
    # 0. Auto-promote: move Estimate→Todo cards whose deps are now met.
    #    Runs FIRST so promoted cards are immediately visible to the pull scan.
    _auto_promote_estimate(board)

    # 1. Handoff → Integrating (worktree=True so integrator sees coder's commits)
    result = _try_stage(board, STAGE_HANDOFF, Action.INTEGRATING, ROLE_INTEGRATOR, worktree=True)
    if result:
        return result

    # 2. Testing
    result = _try_stage_with_forward_wip(board, STAGE_TESTING, Action.TESTING, ROLE_TESTER, STAGE_HANDOFF)
    if result:
        return result
    result = _try_stage(board, STAGE_TESTING, Action.CODING, ROLE_CODER, worktree=True)
    if result:
        return result

    # 3. Review
    result = _try_stage_with_forward_wip(board, STAGE_REVIEW, Action.REVIEWING, ROLE_REVIEWER, STAGE_TESTING)
    if result:
        return result
    result = _try_stage(board, STAGE_REVIEW, Action.CODING, ROLE_CODER, worktree=True)
    if result:
        return result

    # 4. Coding
    result = _try_stage(board, STAGE_CODING, Action.CODING, ROLE_CODER, worktree=True)
    if result:
        return result

    # 5. Todo → Pull to Coding (requires WIP room in 4_Coding)
    if board.has_wip_room(STAGE_CODING):
        card = board.pick_best(STAGE_TODO, Action.CODING)
        if card:
            board.move_card(card, STAGE_CODING, reason="pull: backlog ready")
            return WorkAssignment(card=card, role=ROLE_CODER, needs_worktree=True)

    # 6. Estimate (deps not enforced — architect/product only evaluates)
    result = _try_stage(board, STAGE_ESTIMATE, Action.ARCHITECT, ROLE_ARCHITECT, worktree=False, check_deps=False)
    if result:
        return result
    if board.has_wip_room(STAGE_TODO):
        result = _try_stage(board, STAGE_ESTIMATE, Action.PRODUCT, ROLE_PRODUCT, worktree=False, check_deps=False)
        if result:
            return result

    # 7. Inbox (deps not enforced — product only evaluates)
    result = _try_stage(board, STAGE_INBOX, Action.PRODUCT, ROLE_PRODUCT, worktree=False, check_deps=False)
    if result:
        return result

    return None


def _auto_promote_estimate(board: "KanbanBoard") -> None:
    """Promote Estimate cards with action=Coding to Todo when deps are met.

    Cards get action=Coding in 2_Estimate when product approves them but their
    dependencies are not yet in Done.  This function runs every pull cycle and
    promotes them as soon as deps clear and Todo has WIP room.
    """
    if not board.has_wip_room(STAGE_TODO):
        return
    for card in board.cards_with_action(STAGE_ESTIMATE, Action.CODING):
        if not board.has_unmet_dependencies(card):
            board.move_card(card, STAGE_TODO, reason="pull: deps now met")
            _pull_logger.info("Auto-promoted %s to Todo (deps unblocked)", card.id)
            if not board.has_wip_room(STAGE_TODO):
                break


def find_teamlead_work(board: "KanbanBoard", loop_threshold: int = 2) -> Optional["KanbanCard"]:
    """Find a card that needs teamlead arbitration.

    Returns the highest-priority card with loop_count >= threshold, or a Blocked card.
    """
    blocked = board.blocked_cards()
    if blocked:
        return blocked[0]
    looping = board.looping_cards(loop_threshold)
    if looping:
        return sorted(looping, key=lambda c: -c.loop_count)[0]
    return None


# ── Helpers ─────────────────────────────────────────────────────


def _try_stage(
    board: "KanbanBoard",
    stage: str,
    action: str,
    role: str,
    *,
    worktree: bool,
    check_deps: bool = True,
) -> Optional[WorkAssignment]:
    card = board.pick_best(stage, action, check_deps=check_deps)
    if card:
        return WorkAssignment(card=card, role=role, needs_worktree=worktree)
    return None


def _try_stage_with_forward_wip(
    board: "KanbanBoard",
    stage: str,
    action: str,
    role: str,
    forward_stage: str,
) -> Optional[WorkAssignment]:
    """Try to pick a card, but only if the next stage has WIP room."""
    card = board.pick_best(stage, action)
    if card and board.has_wip_room(forward_stage):
        needs_wt = role in (ROLE_CODER, ROLE_TESTER, ROLE_REVIEWER)
        return WorkAssignment(card=card, role=role, needs_worktree=needs_wt)
    return None
