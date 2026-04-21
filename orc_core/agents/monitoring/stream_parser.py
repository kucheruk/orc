#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stream-line parsing helpers extracted from StreamJsonMonitor.

Pure functions: decode a single agent stdout line into a JSON event and
classify follow-up prompt results. No I/O, no state — so they are
trivially testable in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ...log import log_event


_FOLLOWUP_MARKERS = (
    "add a follow-up",
    "follow-up",
    "follow up",
    "need your input",
    "waiting for your input",
)

_FOLLOWUP_STATUSES = frozenset({"error", "failed", "failure"})


def parse_stream_line(decoded: str, *, log_path: Path) -> Optional[dict]:
    """Decode one agent stdout line as JSON.

    Returns the event dict on success, or None if the line is blank or
    malformed (the error is logged to the orc log, not raised).
    """
    raw = decoded.strip()
    if not raw:
        return None
    try:
        event = json.loads(raw)
    except Exception as exc:
        log_event(log_path, "WARN", "stream_json_bad_line", error=str(exc), raw=raw[:500])
        return None
    return event if isinstance(event, dict) else None


def is_followup_prompt_event(event_type: str, subtype: str, raw: str) -> bool:
    """True if an event indicates the agent is waiting for human input."""
    if event_type != "result":
        return False
    if (subtype or "").strip().lower() not in _FOLLOWUP_STATUSES:
        return False
    normalized = raw.lower()
    return any(marker in normalized for marker in _FOLLOWUP_MARKERS)
