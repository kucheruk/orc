#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracks task progress (done/total/in_progress) and ETA."""

from typing import Optional


class ProgressTracker:
    def __init__(self) -> None:
        self._done = 0
        self._total = 1
        self._in_progress = 0
        self._baseline_total: Optional[int] = None
        self._added_delta = 0
        self._eta_seconds: Optional[float] = None
        self._spinner_idx = 0

    @property
    def done(self) -> int:
        return self._done

    @property
    def total(self) -> int:
        return self._total

    @property
    def in_progress(self) -> int:
        return self._in_progress

    @property
    def added_delta(self) -> int:
        return self._added_delta

    @property
    def eta_seconds(self) -> Optional[float]:
        return self._eta_seconds

    @property
    def spinner_idx(self) -> int:
        return self._spinner_idx

    @property
    def remaining(self) -> int:
        return max(self._total - self._done, 0)

    def set_progress(self, done: int, total: int, in_progress: int = 0) -> None:
        self._done = max(0, int(done))
        self._total = max(1, int(total))
        self._in_progress = max(0, int(in_progress))
        if self._baseline_total is None:
            self._baseline_total = self._total
        self._added_delta = max(self._total - self._baseline_total, 0)

    def set_eta_seconds(self, eta_seconds: Optional[float]) -> None:
        if eta_seconds is None:
            self._eta_seconds = None
            return
        self._eta_seconds = max(float(eta_seconds), 0.0)

    def tick_spinner(self) -> None:
        self._spinner_idx += 1
