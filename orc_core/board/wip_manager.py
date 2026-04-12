#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WIP limit management: enforcement, queries, deadlock detection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .kanban_board_health import detect_wip_deadlock as _detect_wip_deadlock
from .kanban_card import KanbanCard
from .kanban_constants import DEFAULT_WIP_LIMITS, INDEX_FILENAME, STAGES, WIP_STAGES

_logger = logging.getLogger(__name__)


class WIPManager:
    """Manages WIP limits: reads from _index.md, enforces, detects deadlocks."""

    def __init__(self) -> None:
        self._wip_limits: dict[str, int] = dict(DEFAULT_WIP_LIMITS)

    def reset(self) -> None:
        self._wip_limits = dict(DEFAULT_WIP_LIMITS)

    def set_limit_from_index(self, stage: str, limit: int) -> None:
        if isinstance(limit, int) and limit > 0:
            self._wip_limits[stage] = limit

    def wip_limit(self, stage: str) -> int:
        return self._wip_limits.get(stage, 999)

    def has_wip_room(self, stage: str, current_count: int) -> bool:
        if stage not in WIP_STAGES:
            return True
        return current_count < self.wip_limit(stage)

    def wip_free(self, stage: str, current_count: int) -> int:
        if stage not in WIP_STAGES:
            return 999
        return max(0, self.wip_limit(stage) - current_count)

    def check_wip_for_move(self, stage: str, current_count: int) -> None:
        """Raise ValueError if WIP limit reached for the given stage."""
        if stage in WIP_STAGES:
            limit = self._wip_limits.get(stage, 999)
            if current_count >= limit:
                raise ValueError(f"WIP limit reached for {stage}")

    def detect_deadlock(self, cards: list[KanbanCard]) -> str:
        return _detect_wip_deadlock(cards, dict(self._wip_limits))

    def set_limit(self, tasks_dir: Path, stage: str, limit: int, *, repo=None) -> None:
        """Write WIP limit to _index.md and update in-memory cache."""
        if stage not in STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        stage_dir = tasks_dir / stage
        if repo is not None:
            repo.write_index(stage_dir, f"---\nwip_limit: {limit}\n---\n")
        else:
            stage_dir.mkdir(parents=True, exist_ok=True)
            idx = stage_dir / INDEX_FILENAME
            idx.write_text(f"---\nwip_limit: {limit}\n---\n", encoding="utf-8")
        self._wip_limits[stage] = limit
