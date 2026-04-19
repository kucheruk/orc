#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull strategies: one registered strategy per stage→role→action slot.

`find_next_work` iterates over a `StagePullRegistry` in priority order. Each
strategy encapsulates a single pull step (e.g. "pick Handoff→Integrating" or
"promote a Todo card to Coding if Coding has WIP room"). Adding a new SDLC
stage means registering a new strategy, not editing a long if/elif chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Protocol

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
from .stage_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_INBOX,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_TODO,
)

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard
    from .kanban_card import KanbanCard


@dataclass(frozen=True)
class WorkAssignment:
    card: "KanbanCard"
    role: str
    needs_worktree: bool


class StagePullStrategy(Protocol):
    """A single slot in the pull scan. Returns an assignment or None."""

    def try_pull(self, board: "KanbanBoard") -> Optional[WorkAssignment]: ...


@dataclass(frozen=True)
class SimpleStagePull:
    """Pick the best card matching (stage, action) and assign to role."""

    stage: str
    action: str
    role: str
    worktree: bool
    check_deps: bool = True

    def try_pull(self, board: "KanbanBoard") -> Optional[WorkAssignment]:
        card = board.pick_best(self.stage, self.action, check_deps=self.check_deps)
        if card is None:
            return None
        return WorkAssignment(card=card, role=self.role, needs_worktree=self.worktree)


@dataclass(frozen=True)
class ForwardWIPGatedPull:
    """Pick a card only when the downstream stage still has WIP room."""

    stage: str
    action: str
    role: str
    forward_stage: str
    worktree: bool

    def try_pull(self, board: "KanbanBoard") -> Optional[WorkAssignment]:
        card = board.pick_best(self.stage, self.action)
        if card is None or not board.has_wip_room(self.forward_stage):
            return None
        return WorkAssignment(card=card, role=self.role, needs_worktree=self.worktree)


@dataclass(frozen=True)
class BacklogPromotionPull:
    """Promote a Todo card to Coding (side effect: moves the card)."""

    source_stage: str = STAGE_TODO
    target_stage: str = STAGE_CODING
    action: str = Action.CODING
    role: str = ROLE_CODER
    worktree: bool = True
    reason: str = "pull: backlog ready"

    def try_pull(self, board: "KanbanBoard") -> Optional[WorkAssignment]:
        if not board.has_wip_room(self.target_stage):
            return None
        card = board.pick_best(self.source_stage, self.action)
        if card is None:
            return None
        board.move_card(card, self.target_stage, reason=self.reason)
        return WorkAssignment(card=card, role=self.role, needs_worktree=self.worktree)


@dataclass(frozen=True)
class FrontierPull:
    """Pick the Estimate/Inbox candidate that unblocks the most downstream work.

    Optional `wip_room_stage` gates the pull until that stage has WIP room
    (used for Estimate→Product, which must not run if Todo is full).
    """

    stage: str
    action: str
    role: str
    worktree: bool
    wip_room_stage: Optional[str] = None

    def try_pull(self, board: "KanbanBoard") -> Optional[WorkAssignment]:
        if self.wip_room_stage is not None and not board.has_wip_room(self.wip_room_stage):
            return None
        card = _pick_frontier_candidate(board, self.stage, self.action)
        if card is None:
            return None
        return WorkAssignment(card=card, role=self.role, needs_worktree=self.worktree)


def _pick_frontier_candidate(board: "KanbanBoard", stage: str, action: str):
    candidates = board.cards_with_action(stage, action)
    if not candidates:
        return None
    non_done = [c for c in board.cards if c.stage != STAGE_DONE]
    dependent_count: dict[str, int] = {c.id: 0 for c in candidates}
    for candidate in candidates:
        dependent_count[candidate.id] = sum(
            1 for card in non_done if candidate.id in card.dependencies
        )
    ranked = sorted(
        candidates,
        key=lambda card: (-dependent_count.get(card.id, 0), priority_key(card)),
    )
    return ranked[0]


class StagePullRegistry:
    """Ordered registry of pull strategies. First match wins."""

    def __init__(self, strategies: Optional[list[StagePullStrategy]] = None) -> None:
        self._strategies: list[StagePullStrategy] = list(strategies or [])

    def register(self, strategy: StagePullStrategy) -> None:
        self._strategies.append(strategy)

    def find_next(self, board: "KanbanBoard") -> Optional[WorkAssignment]:
        for strategy in self._strategies:
            assignment = strategy.try_pull(board)
            if assignment is not None:
                return assignment
        return None

    def strategies(self) -> list[StagePullStrategy]:
        return list(self._strategies)


def default_registry() -> StagePullRegistry:
    """Build the canonical ORC pull registry (right-to-left SDLC scan)."""
    return StagePullRegistry([
        # 1. Handoff → Integrating
        SimpleStagePull(STAGE_HANDOFF, Action.INTEGRATING, ROLE_INTEGRATOR, worktree=True),
        # 2. Testing
        ForwardWIPGatedPull(STAGE_TESTING, Action.TESTING, ROLE_TESTER, STAGE_HANDOFF, worktree=True),
        SimpleStagePull(STAGE_TESTING, Action.CODING, ROLE_CODER, worktree=True),
        # 3. Review
        ForwardWIPGatedPull(STAGE_REVIEW, Action.REVIEWING, ROLE_REVIEWER, STAGE_TESTING, worktree=True),
        SimpleStagePull(STAGE_REVIEW, Action.CODING, ROLE_CODER, worktree=True),
        # 4. Coding
        SimpleStagePull(STAGE_CODING, Action.CODING, ROLE_CODER, worktree=True),
        # 5. Todo → Coding (with side-effect move)
        BacklogPromotionPull(),
        # 6. Estimate: architect freely, product only if Todo has room
        FrontierPull(STAGE_ESTIMATE, Action.ARCHITECT, ROLE_ARCHITECT, worktree=False),
        FrontierPull(STAGE_ESTIMATE, Action.PRODUCT, ROLE_PRODUCT, worktree=False,
                     wip_room_stage=STAGE_TODO),
        # 7. Inbox
        FrontierPull(STAGE_INBOX, Action.PRODUCT, ROLE_PRODUCT, worktree=False),
    ])
