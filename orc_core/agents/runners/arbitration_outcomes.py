#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strategy pattern for arbitration outcomes — replaces if/elif chains.

Each outcome encapsulates "did this teamlead-arbitration result match X, and
what should the runner do about it?". Matched in declaration order; the first
match wins. Adding a new outcome means adding a new class — no edits to
ArbitrationStep.run().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ...board.action_constants import Action
from ...board.kanban_card import KanbanCard
from ...log import log_event

if TYPE_CHECKING:
    from .teamlead_steps import TeamleadContext


class ArbitrationOutcomeHandler(Protocol):
    """Decides whether a refreshed card matches this outcome and applies it."""

    def matches(self, refreshed: KanbanCard, needs_esc: bool) -> bool: ...

    def apply(
        self,
        ctx: "TeamleadContext",
        card: KanbanCard,
        refreshed: KanbanCard,
        needs_esc: bool,
    ) -> None: ...


class BlockedOutcome:
    """Teamlead explicitly blocked the card → escalate."""

    def matches(self, refreshed: KanbanCard, needs_esc: bool) -> bool:
        return refreshed.action == Action.BLOCKED

    def apply(
        self,
        ctx: "TeamleadContext",
        card: KanbanCard,
        refreshed: KanbanCard,
        needs_esc: bool,
    ) -> None:
        ctx.escalate(refreshed)


class LeftArbitrationOutcome:
    """Teamlead left card in Arbitration without resolving → auto-block + escalate."""

    def matches(self, refreshed: KanbanCard, needs_esc: bool) -> bool:
        return refreshed.action == Action.ARBITRATION

    def apply(
        self,
        ctx: "TeamleadContext",
        card: KanbanCard,
        refreshed: KanbanCard,
        needs_esc: bool,
    ) -> None:
        refreshed.block()
        ctx.distributor.board.save_card(refreshed)
        log_event(
            ctx.log_path,
            "WARN",
            "teamlead left card in Arbitration, auto-blocking",
            task_id=card.id,
        )
        ctx.escalate(refreshed)


class ThresholdResolvedOutcome:
    """Loop count crossed escalation threshold but teamlead resolved → record + log."""

    def matches(self, refreshed: KanbanCard, needs_esc: bool) -> bool:
        return needs_esc

    def apply(
        self,
        ctx: "TeamleadContext",
        card: KanbanCard,
        refreshed: KanbanCard,
        needs_esc: bool,
    ) -> None:
        ctx.outcomes.set_arbitrated_loop(card.id, card.loop_count)
        log_event(
            ctx.log_path,
            "INFO",
            "escalation threshold reached but teamlead resolved — allowing progress",
            task_id=card.id,
            loop_count=refreshed.loop_count,
            action=refreshed.action,
            stage=refreshed.stage,
        )


class ResolvedOutcome:
    """Default: arbitration done normally → record + emit."""

    def matches(self, refreshed: KanbanCard, needs_esc: bool) -> bool:
        return True

    def apply(
        self,
        ctx: "TeamleadContext",
        card: KanbanCard,
        refreshed: KanbanCard,
        needs_esc: bool,
    ) -> None:
        ctx.outcomes.set_arbitrated_loop(card.id, card.loop_count)
        ctx.publisher.emit(
            "arbitration",
            card.id,
            f"{card.id} teamlead resolved → {refreshed.action} "
            f"(loop_count={refreshed.loop_count})",
        )


ARBITRATION_OUTCOMES: tuple[ArbitrationOutcomeHandler, ...] = (
    BlockedOutcome(),
    LeftArbitrationOutcome(),
    ThresholdResolvedOutcome(),
    ResolvedOutcome(),
)
