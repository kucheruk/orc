#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull system: right-to-left scan to find the highest-priority work for a free worker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .kanban_constants import Action

_pull_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard
    from .kanban_card import KanbanCard

# Role names returned by the pull system (mapped to prompt templates)
ROLE_INTEGRATOR = "integrator"
ROLE_TESTER = "tester"
ROLE_REVIEWER = "reviewer"
ROLE_CODER = "coder"
ROLE_ARCHITECT = "architect"
ROLE_PRODUCT = "product"


@dataclass(frozen=True)
class WorkAssignment:
    card: "KanbanCard"
    role: str
    needs_worktree: bool


def find_next_work(board: "KanbanBoard") -> Optional[WorkAssignment]:
    """Scan the board right-to-left and return the best available assignment.

    Returns None if no work is available (all columns empty or WIP-blocked).
    """
    # 1. Handoff → Integrating
    result = _try_stage(board, "7_Handoff", Action.INTEGRATING, ROLE_INTEGRATOR, worktree=False)
    if result:
        return result

    # 2. Testing
    result = _try_stage_with_forward_wip(board, "6_Testing", Action.TESTING, ROLE_TESTER, "7_Handoff")
    if result:
        return result
    result = _try_stage(board, "6_Testing", Action.CODING, ROLE_CODER, worktree=True)
    if result:
        return result

    # 3. Review
    result = _try_stage_with_forward_wip(board, "5_Review", Action.REVIEWING, ROLE_REVIEWER, "6_Testing")
    if result:
        return result
    result = _try_stage(board, "5_Review", Action.CODING, ROLE_CODER, worktree=True)
    if result:
        return result

    # 4. Coding
    result = _try_stage(board, "4_Coding", Action.CODING, ROLE_CODER, worktree=True)
    if result:
        return result

    # 5. Todo → Pull to Coding (requires WIP room in 4_Coding)
    if board.has_wip_room("4_Coding"):
        card = board.pick_best("3_Todo", Action.CODING)
        if card:
            board.move_card(card, "4_Coding", reason="pull: backlog ready")
            return WorkAssignment(card=card, role=ROLE_CODER, needs_worktree=True)

    # 5.5. Promote Estimate cards to Todo when deps are now met
    #   Cards stay in Estimate with action=Coding when deps were unmet at promotion time.
    #   Once deps are satisfied, auto-promote to Todo.
    if board.has_wip_room("3_Todo"):
        for card in board.cards_with_action("2_Estimate", Action.CODING):
            if not board.has_unmet_dependencies(card):
                board.move_card(card, "3_Todo", reason="pull: deps now met")
                _pull_logger.info("Auto-promoted %s to Todo (deps unblocked)", card.id)
                break  # one at a time to respect WIP

    # 6. Estimate (deps not enforced — architect/product only evaluates)
    result = _try_stage(board, "2_Estimate", Action.ARCHITECT, ROLE_ARCHITECT, worktree=False, check_deps=False)
    if result:
        return result
    if board.has_wip_room("3_Todo"):
        result = _try_stage(board, "2_Estimate", Action.PRODUCT, ROLE_PRODUCT, worktree=False, check_deps=False)
        if result:
            return result

    # 7. Inbox (deps not enforced — product only evaluates)
    result = _try_stage(board, "1_Inbox", Action.PRODUCT, ROLE_PRODUCT, worktree=False, check_deps=False)
    if result:
        return result

    return None


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
        needs_wt = role in (ROLE_CODER, ROLE_TESTER)
        return WorkAssignment(card=card, role=role, needs_worktree=needs_wt)
    return None
