#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thread-safe directive queue for teamlead communication."""

from __future__ import annotations

import threading
from typing import Optional


class DirectiveQueue:
    """Thread-safe FIFO queue for human→teamlead directives."""

    def __init__(self) -> None:
        self._queue: list[str] = []
        self._lock = threading.Lock()

    def push(self, text: str) -> None:
        with self._lock:
            self._queue.append(text)

    def pop(self) -> Optional[str]:
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
        return None
