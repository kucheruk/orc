#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keep a task worktree in sync with the canonical board card file."""

from __future__ import annotations

from pathlib import Path

from ..board.kanban_card import KanbanCard


def sync_card_to_worktree(card: KanbanCard, worktree_path: str) -> Path | None:
    """Mirror the canonical card into the task worktree and remove stale copies."""
    if card.file_path is None or not card.file_path.exists():
        return None

    worktree_tasks = Path(worktree_path) / "tasks"
    target_path = worktree_tasks / card.stage / f"{card.id}.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    for stale_path in worktree_tasks.glob(f"*/{card.id}.md"):
        if stale_path != target_path:
            stale_path.unlink(missing_ok=True)

    target_path.write_text(card.file_path.read_text(encoding="utf-8"), encoding="utf-8")
    return target_path
