#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: create a kanban card (inbox or expedite)."""

from __future__ import annotations

from typing import Callable, Optional

from ..board.kanban_board import KanbanBoard
from ..board.kanban_card import KanbanCard
from ..board.kanban_card_factory import KanbanCardFactory


def _factory_for(board: KanbanBoard) -> KanbanCardFactory:
    return KanbanCardFactory(board.tasks_dir, repo=board.repo, clock=board.clock)


def create_inbox_card(
    board: KanbanBoard,
    title: str,
    *,
    card_id: str | None = None,
    on_created: Optional[Callable[[str, str], None]] = None,
) -> KanbanCard:
    """Create a new inbox card and add it to the board."""
    card_id = card_id or board.next_card_id()
    card = _factory_for(board).create_inbox(card_id, title)
    board.register_card(card)
    if on_created:
        on_created(card_id, title)
    return card


def create_expedite_card(
    board: KanbanBoard,
    title: str,
    body: str,
    *,
    card_id: str | None = None,
    stage: str = "3-coding",
    action: str = "Coding",
    cos_justification: str = "",
    on_created: Optional[Callable[[str, str], None]] = None,
) -> KanbanCard:
    """Create an expedite card directly at the given stage."""
    card_id = card_id or board.next_card_id()
    card = _factory_for(board).create_expedite(
        card_id, title, body,
        stage=stage, action=action,
        cos_justification=cos_justification,
    )
    board.register_card(card)
    if on_created:
        on_created(card_id, title)
    return card
