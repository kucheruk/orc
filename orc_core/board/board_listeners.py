#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pub/sub for board card-change events (move, action change)."""

from __future__ import annotations

import logging
import threading
from typing import Callable

_logger = logging.getLogger(__name__)

MoveListener = Callable[[str, str, str, str], None]
ActionChangeListener = Callable[[str, str, str, str], None]


class BoardListenerBus:
    """Register and dispatch card-change listeners, shielding callers from exceptions."""

    def __init__(self, lock: threading.RLock) -> None:
        self._lock = lock
        self._move: list[MoveListener] = []
        self._action_change: list[ActionChangeListener] = []

    def on_move(self, listener: MoveListener) -> None:
        with self._lock:
            self._move.append(listener)

    def on_action_change(self, listener: ActionChangeListener) -> None:
        with self._lock:
            self._action_change.append(listener)

    def fire_move(self, card_id: str, old_stage: str, new_stage: str, reason: str) -> None:
        with self._lock:
            listeners = list(self._move)
        for listener in listeners:
            try:
                listener(card_id, old_stage, new_stage, reason)
            except Exception:
                _logger.warning("on_move listener failed for %s", card_id, exc_info=True)

    def fire_action_change(self, card_id: str, old_action: str, new_action: str, role: str) -> None:
        with self._lock:
            listeners = list(self._action_change)
        for listener in listeners:
            try:
                listener(card_id, old_action, new_action, role)
            except Exception:
                _logger.warning("on_action_change listener failed for %s", card_id, exc_info=True)
