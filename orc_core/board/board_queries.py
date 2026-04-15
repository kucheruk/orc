#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derived/filtered views over the board state: loops, blocked, deps, summary."""

from __future__ import annotations

import threading
from typing import Callable

from .kanban_card import KanbanCard
from .stage_constants import STAGES
from .wip_manager import WIPManager

CardsView = Callable[[], list[KanbanCard]]


class BoardQueries:
    """Aggregate and filter helpers built on the cards/WIP state."""

    def __init__(
        self,
        *,
        cards_view: CardsView,
        wip: WIPManager,
        lock: threading.RLock,
    ) -> None:
        self._cards_view = cards_view
        self._wip = wip
        self._lock = lock

    def looping(self, threshold: int = 2) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards_view()
                    if c.is_looping(threshold) and not c.is_assigned
                    and not c.is_done]

    def blocked(self) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards_view()
                    if c.is_blocked and not c.is_assigned
                    and not c.is_done]

    def has_unmet_dependencies(self, card: KanbanCard) -> bool:
        if not card.dependencies:
            return False
        with self._lock:
            done_ids = {c.id for c in self._cards_view() if c.is_done}
        return any(dep not in done_ids for dep in card.dependencies)

    def summary(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        with self._lock:
            counts = {s: 0 for s in STAGES}
            for c in self._cards_view():
                if c.stage in counts:
                    counts[c.stage] += 1
        for stage in STAGES:
            raw_limit = self._wip.wip_limit(stage)
            limit = raw_limit if raw_limit != 999 else 0
            result[stage] = {"count": counts[stage], "wip_limit": limit}
        return result
