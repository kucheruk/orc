#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write single-card mutations back to the filesystem via CardRepository."""

from __future__ import annotations

import threading

from .board_listeners import BoardListenerBus
from .card_repository import CardRepository
from .kanban_card import KanbanCard


class BoardCardPersistence:
    """Apply and persist mutations to a single card (save, assign, release)."""

    def __init__(
        self,
        *,
        repo: CardRepository,
        lock: threading.RLock,
        listeners: BoardListenerBus,
    ) -> None:
        self._repo = repo
        self._lock = lock
        self._listeners = listeners

    def save(self, card: KanbanCard, *, old_action: str = "", role: str = "") -> None:
        with self._lock:
            card.touch()  # touch() includes refresh_roi()
            card.advance_state_version()
            if card.file_path:
                self._repo.write_card_text(card.file_path, card.to_markdown())
        if old_action and old_action != card.action:
            self._listeners.fire_action_change(card.id, old_action, card.action, role)

    def assign(self, card: KanbanCard, agent_id: str) -> None:
        with self._lock:
            card.assign(agent_id)
            card.advance_state_version()
            if card.file_path:
                self._repo.write_card_text(card.file_path, card.to_markdown())

    def release(self, card: KanbanCard) -> None:
        with self._lock:
            card.release()
            card.advance_state_version()
            if card.file_path:
                self._repo.write_card_text(card.file_path, card.to_markdown())
