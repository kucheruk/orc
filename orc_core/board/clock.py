#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clock port — domain code reads time through this, not through datetime/time directly."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    """Port for reading current time. Inject to make domain code testable."""

    def now(self) -> datetime: ...

    def monotonic(self) -> float: ...

    def now_iso(self) -> str: ...


class SystemClock:
    """Default Clock implementation bound to the system wall clock."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        import time as _time
        return _time.monotonic()

    def now_iso(self) -> str:
        return self.now().isoformat(timespec="seconds")
