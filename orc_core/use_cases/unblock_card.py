#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: unblock a kanban card with a human directive."""

from __future__ import annotations

from typing import Callable, Optional

from ..board.kanban_board import KanbanBoard
from ..board.action_constants import Action


def unblock_card(
    board: KanbanBoard,
    card_id: str,
    directive: str,
    *,
    on_unblocked: Optional[Callable[[str, str], None]] = None,
) -> bool:
    """Unblock a card. Returns True if the card was found and unblocked."""
    card = board.card_by_id(card_id)
    if card is None or card.action != Action.BLOCKED:
        return False
    card.unblock(directive)
    board.save_card(card)
    if on_unblocked:
        on_unblocked(card_id, directive)
    return True
