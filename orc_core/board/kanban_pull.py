#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull system: right-to-left scan to find the highest-priority work for a free worker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .action_constants import Action
from .card_prioritizer import priority_key
from .limits_constants import DECOMPOSITION_EFFORT_THRESHOLD
from .stage_constants import STAGE_CODING, STAGE_DONE, STAGE_ESTIMATE, STAGE_HANDOFF, STAGE_INBOX, STAGE_REVIEW, STAGE_TESTING, STAGE_TODO

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
    # 0a. Auto-archive: retire parent cards that were already decomposed into
    #     `{id}-A`, `{id}-B`, ... sub-cards. Otherwise the architect keeps
    #     re-pulling the parent and burns tokens in a decomposition death loop.
    _auto_archive_decomposed_parents(board)

    # 0b. Defensive budget reset: if a card is budget-exhausted but not
    #     currently Blocked, something unblocked it (teamlead arbitration, a
    #     manual move, ...) without refreshing tokens_spent. pick_best filters
    #     exhausted cards, so the 'unblocked' card would be stuck invisible.
    #     Treat non-BLOCKED + exhausted as a recovery signal and drain tokens.
    _reset_orphaned_exhausted_budgets(board)

    # 0c. Auto-promote: move Estimate→Todo cards whose deps are now met.
    #     Runs FIRST so promoted cards are immediately visible to the pull scan.
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
    result = _try_stage_frontier(board, STAGE_ESTIMATE, Action.ARCHITECT, ROLE_ARCHITECT, worktree=False)
    if result:
        return result
    if board.has_wip_room(STAGE_TODO):
        result = _try_stage_frontier(board, STAGE_ESTIMATE, Action.PRODUCT, ROLE_PRODUCT, worktree=False)
        if result:
            return result

    # 7. Inbox (deps not enforced — product only evaluates)
    result = _try_stage_frontier(board, STAGE_INBOX, Action.PRODUCT, ROLE_PRODUCT, worktree=False)
    if result:
        return result

    return None


def _auto_archive_decomposed_parents(board: "KanbanBoard") -> None:
    """Retire Estimate cards that already have `{id}-X` sub-cards.

    The architect prompt instructs the agent to split oversized or
    multi-topic cards into sub-cards `{id}-A`, `{id}-B`, ...  Historically the
    parent card file was expected to be deleted by the agent, but ORC's output
    validator rejects missing-file writes and reverts the edit, so the parent
    survives in STAGE_ESTIMATE with `action=Blocked` or `action=Product` and
    `effort_score=0`. The architect then re-pulls it on the next cycle and
    burns another 100K+ tokens re-splitting the same card.

    This sweep breaks the loop: if any card whose id starts with `{parent}-`
    exists in any stage, the parent is moved to STAGE_DONE with `action=Done`
    (and never re-enters the pull scan). The move does not touch source code,
    so it does not need the integrator path — the parent card carries no
    worktree, its scope is fully replaced by the sub-cards.
    """
    from .stage_constants import STAGE_DONE

    all_ids = [c.id for c in board.cards]
    id_set = set(all_ids)
    # Index which parents have at least one sub-card on the board.
    decomposed_parents: set[str] = set()
    for cid in all_ids:
        # A sub-card id looks like "{parent}-{suffix}" where suffix is a
        # single uppercase letter (A, B, C, ...). Only accept that shape to
        # avoid false positives on ids that legitimately contain dashes.
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
        # Only archive parents that still live in Estimate/Inbox — if an agent
        # already picked the parent into coding, let that flow complete.
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
    (e.g. teamlead arbitration written by an older ORC version, a manual
    action edit, or a future unblock path that forgets the refresh). When
    that happens, `card_prioritizer.pick_best` silently drops the card
    because `is_budget_exhausted` is True and the board stalls.

    We do NOT reset tokens_spent: worker's `_accumulate_card_tokens` reads
    the cumulative stats file and would immediately restore it, triggering
    an infinite block↔sweep loop. Instead, bump token_budget so
    `tokens_spent < token_budget` holds for another full effort-sized run.

    Grown budgets survive across saves; the sweep is idempotent because
    once budget > tokens_spent the card is no longer exhausted and skipped.
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
    """Promote Estimate cards with action=Coding to Todo when deps are met.

    Cards get action=Coding in 2_Estimate when product approves them but their
    dependencies are not yet in Done.  This function runs every pull cycle and
    promotes them as soon as deps clear and Todo has WIP room.
    """
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
        return sorted(arbitration, key=priority_key)[0]
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


def _try_stage_frontier(
    board: "KanbanBoard",
    stage: str,
    action: str,
    role: str,
    *,
    worktree: bool,
) -> Optional[WorkAssignment]:
    card = _pick_frontier_candidate(board, stage, action)
    if card:
        return WorkAssignment(card=card, role=role, needs_worktree=worktree)
    return None


def _pick_frontier_candidate(board: "KanbanBoard", stage: str, action: str):
    candidates = board.cards_with_action(stage, action)
    if not candidates:
        return None
    non_done = [c for c in board.cards if c.stage != STAGE_DONE]
    dependent_count: dict[str, int] = {c.id: 0 for c in candidates}
    for candidate in candidates:
        dependent_count[candidate.id] = sum(1 for card in non_done if candidate.id in card.dependencies)
    ranked = sorted(
        candidates,
        key=lambda card: (-dependent_count.get(card.id, 0), priority_key(card)),
    )
    return ranked[0]
