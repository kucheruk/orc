#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restart policy — backoff, max-restart gate, continue-prompt building.

Encapsulates decisions previously inlined in _run_stage_loop so that
the stage orchestrator can stay focused on stage sequencing.
"""

from __future__ import annotations

from typing import Mapping

from ...models.task_status import RESTART_REASON_TEXT


class RestartPolicy:
    """Governs restart decisions for a stage retry loop."""

    def __init__(self, *, max_restarts: int, reason_text: Mapping[str, str] = RESTART_REASON_TEXT) -> None:
        self._max_restarts = max_restarts
        self._reason_text = reason_text

    @property
    def max_restarts(self) -> int:
        return self._max_restarts

    def exceeded(self, restart_count: int) -> bool:
        """True iff we've burned through the retry budget."""
        return restart_count > self._max_restarts

    def backoff_seconds(self, restart_count: int) -> float:
        """Deterministic capped backoff prevents rapid restart storms."""
        return float(min(2 ** max(restart_count - 1, 0), 30))

    def reason_text(self, result: str) -> str:
        return self._reason_text.get(result, result)
