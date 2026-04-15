#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: split a parent card into N subcards and mark parent Done."""

from __future__ import annotations

from ...board.kanban_board import KanbanBoard
from ...board.kanban_card import KanbanCard
from ...board.stage_constants import STAGE_DONE
from .create_card import create_inbox_card


def split_card(
    board: KanbanBoard,
    parent: KanbanCard,
    sub_titles: list[str],
) -> list[KanbanCard]:
    """Split parent card into subcards via create_inbox_card. Mark parent as Done."""
    subcards = [create_inbox_card(board, title) for title in sub_titles]
    if parent.stage != STAGE_DONE:
        board.move_card(parent, STAGE_DONE, allow_backward=False, reason="split into subcards")
    return subcards
