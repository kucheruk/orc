#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: mark a task's card as Blocked with a reason."""

from __future__ import annotations

from ...board.gateway import BoardGateway, CardView
from ...board.use_cases.escalate_card import escalate_card


def mark_task_blocked(card: CardView, board: BoardGateway, *, reason: str) -> None:
    """Block the card with the given reason and persist it through the board port."""
    escalate_card(board, card, reason=reason)
