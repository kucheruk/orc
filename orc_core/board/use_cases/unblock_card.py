#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: unblock a kanban card with a human directive."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ...board.kanban_board import KanbanBoard
from ...board.action_constants import Action
from ...log import log_event


def unblock_card(
    board: KanbanBoard,
    card_id: str,
    directive: str,
    *,
    publisher: Optional[Any] = None,
    log_path: Optional[Path] = None,
) -> bool:
    """Unblock a card with a directive. Returns True if the card was unblocked.

    Emits log + publisher events when those dependencies are supplied, so
    delivery layers can call the use case directly.
    """
    card = board.card_by_id(card_id)
    if card is None or card.action != Action.BLOCKED:
        return False
    card.unblock(directive)
    board.save_card(card)
    if log_path is not None:
        log_event(log_path, "INFO", "card unblocked", card_id=card_id, directive=directive)
    if publisher is not None:
        publisher.log_unblock(card_id, directive)
    from ...signals import SignalKind, emit_signal
    emit_signal(
        SignalKind.CARD_UNBLOCKED,
        "operator_directive" if directive else "operator",
        task_id=card_id,
        context={"directive": (directive or "")[:300]},
    )
    return True
