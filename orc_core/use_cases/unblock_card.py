#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: unblock a kanban card with a human directive."""

from __future__ import annotations

from pathlib import Path

from ..board.kanban_board import KanbanBoard
from ..board.action_constants import Action
from ..infra.io.logging import log_event


def unblock_card(
    board: KanbanBoard,
    card_id: str,
    directive: str,
    *,
    log_path: Path | None = None,
) -> bool:
    """Unblock a card. Returns True if the card was found and unblocked."""
    card = board.card_by_id(card_id)
    if card is None or card.action != Action.BLOCKED:
        return False
    card.unblock(directive)
    board.save_card(card)
    if log_path:
        log_event(log_path, "INFO", "card unblocked", card_id=card_id, directive=directive)
    return True
