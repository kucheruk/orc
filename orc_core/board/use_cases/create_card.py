#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: create a kanban card (inbox or expedite)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ...board.action_constants import Action
from ...board.kanban_board import KanbanBoard
from ...board.kanban_card import KanbanCard
from ...board.kanban_card_factory import KanbanCardFactory
from ...log import log_event


def _factory_for(board: KanbanBoard) -> KanbanCardFactory:
    return KanbanCardFactory(board.tasks_dir, repo=board.repo, clock=board.clock)


def _notify_created(
    card: KanbanCard,
    title: str,
    *,
    publisher: Optional[Any],
    log_path: Optional[Path],
    is_expedite: bool,
) -> None:
    if log_path is not None:
        event = "expedite card created" if is_expedite else "inbox card created"
        log_event(log_path, "INFO", event, card_id=card.id, title=title)
    if publisher is not None:
        publisher.log_inbox(card.id, title)


def create_inbox_card(
    board: KanbanBoard,
    title: str,
    *,
    card_id: str | None = None,
    publisher: Optional[Any] = None,
    log_path: Optional[Path] = None,
) -> KanbanCard:
    """Create a new inbox card and add it to the board.

    When ``publisher`` and/or ``log_path`` are supplied, the use case emits
    the creation event through them — so delivery layers (TUI, CLI) can
    invoke the use case directly without needing a session wrapper.
    """
    resolved_id = card_id or board.next_card_id()
    card = _factory_for(board).create_inbox(resolved_id, title)
    board.register_card(card)
    _notify_created(card, title, publisher=publisher, log_path=log_path, is_expedite=False)
    return card


def create_expedite_card(
    board: KanbanBoard,
    title: str,
    body: str,
    *,
    card_id: str | None = None,
    stage: str = "3-coding",
    action: str = Action.CODING,
    cos_justification: str = "",
    publisher: Optional[Any] = None,
    log_path: Optional[Path] = None,
) -> KanbanCard:
    """Create an expedite card directly at the given stage."""
    resolved_id = card_id or board.next_card_id()
    card = _factory_for(board).create_expedite(
        resolved_id, title, body,
        stage=stage, action=action,
        cos_justification=cos_justification,
    )
    board.register_card(card)
    _notify_created(card, title, publisher=publisher, log_path=log_path, is_expedite=True)
    return card
