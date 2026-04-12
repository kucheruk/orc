#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Board summary formatting for prompts — lives in board/ to avoid circular deps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .stage_constants import STAGES

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard


def format_board_summary(board: "KanbanBoard") -> str:
    """Format board state as a compact text table for prompts."""
    lines = ["| Stage | Cards | WIP Limit | Free |"]
    lines.append("|-------|-------|-----------|------|")
    summary = board.summary()
    for stage in STAGES:
        info = summary.get(stage, {"count": 0, "wip_limit": 0})
        count = info["count"]
        limit = info["wip_limit"]
        free = max(0, limit - count) if limit > 0 else "∞"
        lines.append(f"| {stage} | {count} | {limit or '∞'} | {free} |")
    return "\n".join(lines)
