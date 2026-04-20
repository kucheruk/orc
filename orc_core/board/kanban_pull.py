#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull system: right-to-left scan for the highest-priority work.

The actual slot-by-slot pull logic lives in `pull_strategies.py` as an
ordered `StagePullRegistry`. This module orchestrates the scan:
pre-flight sweeps (archive decomposed parents, reset orphaned budgets,
promote ready Estimate cards) and then delegate to the registry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .action_constants import Action
from .card_prioritizer import priority_key
from .kanban_role_registry import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TESTER,
)
from .limits_constants import DECOMPOSITION_EFFORT_THRESHOLD
from .pull_strategies import StagePullRegistry, WorkAssignment, default_registry
from .stage_constants import STAGE_DONE, STAGE_ESTIMATE, STAGE_INBOX, STAGE_TODO

_pull_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard
    from .kanban_card import KanbanCard


# Re-export so existing importers keep working.
__all__ = [
    "WorkAssignment",
    "find_next_work",
    "find_teamlead_work",
    "ROLE_ARCHITECT",
    "ROLE_CODER",
    "ROLE_INTEGRATOR",
    "ROLE_PRODUCT",
    "ROLE_REVIEWER",
    "ROLE_TESTER",
]


_DEFAULT_REGISTRY: StagePullRegistry = default_registry()


def find_next_work(
    board: "KanbanBoard",
    *,
    registry: Optional[StagePullRegistry] = None,
) -> Optional[WorkAssignment]:
    """Run pre-flight sweeps, then scan the registry for the next assignment."""
    _auto_archive_decomposed_parents(board)
    _reset_orphaned_exhausted_budgets(board)
    _auto_promote_estimate(board)
    return (registry or _DEFAULT_REGISTRY).find_next(board)


def _auto_archive_decomposed_parents(board: "KanbanBoard") -> None:
    """Retire Estimate cards that already have `{id}-X` sub-cards.

    The architect prompt instructs the agent to split oversized or
    multi-topic cards into sub-cards `{id}-A`, `{id}-B`, ...  Historically the
    parent card file was expected to be deleted by the agent, but ORC's output
    validator rejects missing-file writes and reverts the edit, so the parent
    survives in STAGE_ESTIMATE with `action=Blocked` or `action=Product` and
    `effort_score=0`. The architect then re-pulls it on the next cycle and
    burns another 100K+ tokens re-splitting the same card.
    """
    all_ids = [c.id for c in board.cards]
    id_set = set(all_ids)
    decomposed_parents: set[str] = set()
    for cid in all_ids:
        if "-" not in cid:
            continue
        parent, _, suffix = cid.rpartition("-")
        if not parent or len(suffix) != 1 or not suffix.isalpha() or not suffix.isupper():
            continue
        if parent in id_set:
            decomposed_parents.add(parent)

    if not decomposed_parents:
        return

    for parent_id in decomposed_parents:
        parent = board.card_by_id(parent_id)
        if parent is None or parent.stage == STAGE_DONE:
            continue
        if parent.stage not in (STAGE_ESTIMATE, STAGE_INBOX):
            continue
        _pull_logger.warning(
            "Archiving decomposed parent %s (sub-cards already exist); "
            "avoids architect death-loop on re-pull.",
            parent_id,
        )
        parent.action = Action.DONE
        board.move_card(parent, STAGE_DONE, allow_backward=False,
                        reason="auto-archive: decomposed into sub-cards")
        board.save_card(parent)


def _reset_orphaned_exhausted_budgets(board: "KanbanBoard") -> None:
    """Grow token_budget on non-BLOCKED cards that are still budget-exhausted.

    Invariant: if action != BLOCKED, the card is supposed to be eligible for
    pick_best. A card can escape BLOCKED without its budget being refreshed
    (e.g. teamlead arbitration written by an older ORC version). We do NOT
    reset tokens_spent: worker's `_accumulate_card_tokens` reads the cumulative
    stats file and would immediately restore it, triggering an infinite
    block↔sweep loop.
    """
    from .limits_constants import TOKENS_PER_EFFORT_POINT
    for card in board.cards:
        if card.action == Action.BLOCKED:
            continue
        if not card.is_budget_exhausted:
            continue
        extra = max(
            card.effort_score * TOKENS_PER_EFFORT_POINT,
            TOKENS_PER_EFFORT_POINT,
        )
        _pull_logger.warning(
            "Orphaned exhausted budget on %s (action=%s, tokens_spent=%d, "
            "token_budget=%d) — growing token_budget by %d so pick_best "
            "can see the card.",
            card.id, card.action, card.tokens_spent, card.token_budget, extra,
        )
        card.token_budget += extra
        board.save_card(card)


def _auto_promote_estimate(board: "KanbanBoard") -> None:
    """Promote Estimate cards with action=Coding to Todo when deps are met."""
    if not board.has_wip_room(STAGE_TODO):
        return
    for card in board.cards_with_action(STAGE_ESTIMATE, Action.CODING):
        if card.effort_score > DECOMPOSITION_EFFORT_THRESHOLD:
            previous_effort = card.effort_score
            _pull_logger.warning(
                "Blocked %s from Todo: effort_score %d > %d, sent back to Architect for decomposition",
                card.id, previous_effort, DECOMPOSITION_EFFORT_THRESHOLD)
            card.action = Action.ARCHITECT
            card.effort_score = 0
            board.save_card(card)
            continue
        if not board.has_unmet_dependencies(card):
            board.move_card(card, STAGE_TODO, reason="pull: deps now met")
            _pull_logger.info("Auto-promoted %s to Todo (deps unblocked)", card.id)
            if not board.has_wip_room(STAGE_TODO):
                break


def find_teamlead_work(board: "KanbanBoard", loop_threshold: int = 2) -> Optional["KanbanCard"]:
    """Find a card that needs teamlead arbitration.

    Priority: blocked > arbitration-requested > high loop_count.
    """
    blocked = board.blocked_cards()
    if blocked:
        return blocked[0]
    arbitration = board.arbitration_cards()
    if arbitration:
        from .card_prioritizer import build_downstream_roi_map
        downstream = build_downstream_roi_map(board.cards)
        return sorted(arbitration, key=lambda c: priority_key(c, downstream))[0]
    looping = board.looping_cards(loop_threshold)
    if looping:
        return sorted(looping, key=lambda c: -c.loop_count)[0]
    return None
