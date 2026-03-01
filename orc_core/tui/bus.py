#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
from typing import Optional

from ..stream_monitor_state import MonitorSnapshot

_LOCK = threading.Lock()
_LATEST_SNAPSHOT: Optional[MonitorSnapshot] = None


def publish_snapshot(snapshot: MonitorSnapshot) -> None:
    global _LATEST_SNAPSHOT
    with _LOCK:
        _LATEST_SNAPSHOT = snapshot


def consume_latest_snapshot() -> Optional[MonitorSnapshot]:
    global _LATEST_SNAPSHOT
    with _LOCK:
        snapshot = _LATEST_SNAPSHOT
        _LATEST_SNAPSHOT = None
    return snapshot
