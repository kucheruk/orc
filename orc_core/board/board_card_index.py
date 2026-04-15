#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-card lock registry, card registration, and filesystem lookup by id."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional

from .kanban_card import KanbanCard
from .stage_constants import STAGES

CardsView = Callable[[], list[KanbanCard]]


class BoardCardIndex:
    """Index operations over cards: locks per id, registration, file lookup."""

    def __init__(
        self,
        tasks_dir: Path,
        *,
        cards_view: CardsView,
        lock: threading.RLock,
    ) -> None:
        self._tasks_dir = tasks_dir
        self._cards_view = cards_view
        self._lock = lock
        self._card_locks: dict[str, threading.Lock] = {}

    def get_card_lock(self, card_id: str) -> threading.Lock:
        with self._lock:
            if card_id not in self._card_locks:
                self._card_locks[card_id] = threading.Lock()
            return self._card_locks[card_id]

    @contextmanager
    def locked_card(self, card_id: str) -> Iterator[None]:
        with self.get_card_lock(card_id):
            yield

    def register(self, card: KanbanCard) -> None:
        with self._lock:
            self._cards_view().append(card)

    def next_id(self) -> str:
        with self._lock:
            nums = []
            for c in self._cards_view():
                parts = c.id.rsplit("-", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    nums.append(int(parts[1]))
            next_num = max(nums, default=0) + 1
        return f"TASK-{next_num:03d}"

    def find_file(self, card_id: str) -> Optional[Path]:
        filename = f"{card_id}.md"
        for stage in STAGES:
            candidate = self._tasks_dir / stage / filename
            if candidate.exists():
                return candidate
        return None
