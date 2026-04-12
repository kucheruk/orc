#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: move a kanban card between stages with all side effects."""

from __future__ import annotations

from ..board.kanban_board import KanbanBoard
from ..board.kanban_card import KanbanCard


def move_card(
    board: KanbanBoard,
    card: KanbanCard,
    target_stage: str,
    *,
    reason: str = "",
    allow_backward: bool = False,
) -> None:
    """Move card to target_stage, enforcing WIP limits and firing board listeners."""
    board.move_card(card, target_stage, allow_backward=allow_backward, reason=reason)
