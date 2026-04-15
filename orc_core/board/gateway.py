#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BoardGateway — external-domain port for the kanban board.

External bounded contexts (tasks, git) depend on these Protocols instead of the
concrete KanbanBoard / KanbanCard. Python's structural Protocol makes this a pure
type-level abstraction: KanbanBoard and KanbanCard already satisfy the shapes and
need no runtime changes.

Use cases declare parameters as BoardGateway / CardView; implementations pass the
concrete KanbanBoard / KanbanCard unchanged.
"""

from __future__ import annotations

from typing import Optional, Protocol


class CardView(Protocol):
    """Read/write facade over a kanban card used by external use cases."""

    id: str
    title: str
    stage: str
    action: str
    class_of_service: str

    def block(self, reason: str = "") -> None: ...


class BoardGateway(Protocol):
    """Port exposing the subset of KanbanBoard operations needed by external use cases."""

    def save_card(self, card: CardView) -> None: ...

    def move_card(
        self,
        card: CardView,
        to_stage: str,
        *,
        allow_backward: bool = False,
        reason: str = "",
    ) -> None: ...

    def card_by_id(self, card_id: str) -> Optional[CardView]: ...
