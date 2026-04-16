#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: escalate a card by blocking it and moving to Handoff."""

from __future__ import annotations

from ...board.gateway import BoardGateway, CardView
from ...board.stage_constants import STAGE_HANDOFF


def escalate_card(board: BoardGateway, card: CardView, *, reason: str = "") -> None:
    """Block the card and move it to Handoff for human attention."""
    card.block(reason)
    board.save_card(card)
    if card.stage != STAGE_HANDOFF:
        board.move_card(card, STAGE_HANDOFF, allow_backward=True, reason=reason or "escalated")
