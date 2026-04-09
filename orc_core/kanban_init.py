#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize the kanban board folder structure."""

from pathlib import Path

from .kanban_constants import DEFAULT_WIP_LIMITS, INDEX_FILENAME, STAGES, WIP_STAGES


def init_kanban_board(root: Path) -> Path:
    """Create tasks/ directory with stage folders and _index.md files.

    Returns the tasks/ directory path.
    """
    tasks_dir = root / "tasks"
    tasks_dir.mkdir(exist_ok=True)

    for stage in STAGES:
        stage_dir = tasks_dir / stage
        stage_dir.mkdir(exist_ok=True)

        if stage in WIP_STAGES:
            idx_path = stage_dir / INDEX_FILENAME
            if not idx_path.exists():
                limit = DEFAULT_WIP_LIMITS.get(stage, 5)
                idx_path.write_text(
                    f"---\nstage: {stage}\nwip_limit: {limit}\n---\n",
                    encoding="utf-8",
                )

    gitkeep = tasks_dir / "8_Done" / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    return tasks_dir
