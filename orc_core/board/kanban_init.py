#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize the kanban board folder structure."""

from __future__ import annotations

from pathlib import Path

from .card_repository import CardRepository
from .limits_constants import DEFAULT_WIP_LIMITS, INDEX_FILENAME, WIP_STAGES
from .stage_constants import STAGES, STAGE_DONE


def init_kanban_board(root: Path, *, repo: CardRepository | None = None) -> Path:
    """Create tasks/ directory with stage folders and _index.md files.

    Returns the tasks/ directory path. All filesystem writes go through the
    ``CardRepository`` port; if none is supplied a default ``FsCardRepository``
    is instantiated.
    """
    if repo is None:
        from .fs_card_repository import FsCardRepository
        repo = FsCardRepository()

    tasks_dir = root / "tasks"
    repo.ensure_dir(tasks_dir)

    for stage in STAGES:
        stage_dir = tasks_dir / stage
        repo.ensure_dir(stage_dir)

        if stage in WIP_STAGES:
            idx_path = stage_dir / INDEX_FILENAME
            if not idx_path.exists():
                limit = DEFAULT_WIP_LIMITS.get(stage, 5)
                repo.write_index(
                    stage_dir,
                    f"---\nstage: {stage}\nwip_limit: {limit}\n---\n",
                )

    done_dir = tasks_dir / STAGE_DONE
    gitkeep = done_dir / ".gitkeep"
    if not gitkeep.exists():
        repo.write_card_text(gitkeep, "")

    return tasks_dir
