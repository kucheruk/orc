#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracks task completion/failure outcomes with thread-safe mutation."""

from __future__ import annotations

import threading


class TaskOutcomeTracker:
    """Thread-safe tracker for card outcomes: completions, failures, fail counts.

    Replaces shared mutable dicts/lists passed by reference between
    KanbanSessionManager and KanbanWorkerRunner.
    """

    def __init__(
        self,
        card_fail_counts: dict[str, int] | None = None,
        arbitrated_at_loop: dict[str, int] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._completed: list[str] = []
        self._failed: list[str] = []
        self._card_fail_counts: dict[str, int] = dict(card_fail_counts or {})
        self._arbitrated_at_loop: dict[str, int] = dict(arbitrated_at_loop or {})
        self._dirty = False

    # ── Outcome recording ───────────────────────────────────────

    def record_completed(self, card_id: str) -> None:
        with self._lock:
            self._completed.append(card_id)

    def record_failed(self, card_id: str) -> None:
        with self._lock:
            self._failed.append(card_id)

    # ── Fail count management ───────────────────────────────────

    def increment_fail_count(self, card_id: str) -> int:
        """Increment and return the new fail count."""
        with self._lock:
            count = self._card_fail_counts.get(card_id, 0) + 1
            self._card_fail_counts[card_id] = count
            self._dirty = True
            return count

    def reset_fail_count(self, card_id: str) -> None:
        with self._lock:
            if card_id in self._card_fail_counts:
                del self._card_fail_counts[card_id]
                self._dirty = True

    def get_fail_count(self, card_id: str) -> int:
        with self._lock:
            return self._card_fail_counts.get(card_id, 0)

    # ── Arbitration tracking ────────────────────────────────────

    @property
    def arbitrated_at_loop(self) -> dict[str, int]:
        return self._arbitrated_at_loop

    # ── State persistence ───────────────────────────────────────

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def clear_dirty(self) -> None:
        self._dirty = False

    def state_snapshot(self) -> dict:
        """Return serializable state for persistence."""
        with self._lock:
            return {
                "card_fail_counts": dict(self._card_fail_counts),
                "arbitrated_at_loop": dict(self._arbitrated_at_loop),
            }

    # ── Read-only queries ───────────────────────────────────────

    @property
    def completed_tasks(self) -> list[str]:
        with self._lock:
            return list(self._completed)

    @property
    def failed_tasks(self) -> list[str]:
        with self._lock:
            return list(self._failed)
