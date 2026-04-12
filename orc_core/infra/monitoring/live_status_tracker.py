#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracks the live phase/status shown in the TUI session panel."""

import time
from typing import Dict, Optional

from .reasoning_tracker import ReasoningTracker
from .tool_call_tracker import ToolCallTracker


class LiveStatusTracker:
    """Manages live_phase, live_status, and is_subagent_activity state."""

    def __init__(self, started_at: float) -> None:
        self.phase = "starting"
        self.status = "starting, no messages yet"
        self.since = started_at
        self.is_subagent_activity = False

    def set(self, phase: str, status: str, *, is_subagent: Optional[bool] = None) -> None:
        normalized_phase = str(phase or "waiting").strip() or "waiting"
        normalized_status = str(status or "").strip() or "waiting for output"
        normalized_subagent = self.is_subagent_activity if is_subagent is None else bool(is_subagent)
        if (
            normalized_phase != self.phase
            or normalized_status != self.status
            or normalized_subagent != self.is_subagent_activity
        ):
            self.phase = normalized_phase
            self.status = normalized_status
            self.is_subagent_activity = normalized_subagent
            self.since = time.time()

    def update_from_event(
        self,
        event: Dict[str, object],
        event_type: str,
        subtype: str,
        text: str,
        reasoning: ReasoningTracker,
        tools: ToolCallTracker,
    ) -> None:
        if event_type in {"thinking", "analysis"}:
            fragment = reasoning._extract_reasoning_fragment(event, text)
            preview = reasoning._trim_fragment(" ".join(fragment.split()).strip()) if fragment else ""
            status = f"thinking {preview}" if preview else "thinking"
            self.set("thinking", status, is_subagent=False)
        elif event_type == "assistant":
            self.set("assistant", "responding", is_subagent=False)
        elif event_type == "result":
            status = str(event.get("status") or subtype or "result").strip().lower() or "result"
            self.set("waiting", f"result {status}", is_subagent=False)
        elif self._update_for_network_event(event, event_type, subtype):
            pass
        elif event_type != "tool_call" and tools.active_tool_calls:
            label, is_subagent = tools._active_tool_status()
            self.set(
                "subagent" if is_subagent else "tool_call",
                f"running {label}",
                is_subagent=is_subagent,
            )
        elif event_type not in {"tool_call", "thinking", "analysis", "assistant", "result"}:
            self.set("waiting", "waiting for output", is_subagent=False)

    def _update_for_network_event(self, event: Dict[str, object], event_type: str, subtype: str) -> bool:
        event_lower = str(event_type or "").strip().lower()
        subtype_lower = str(subtype or "").strip().lower()
        if event_lower not in {"connection", "retry"}:
            return False

        if event_lower == "connection":
            if subtype_lower in {"reconnecting", "disconnected", "degraded"}:
                self.set("network_problem", "Network problems: reconnecting", is_subagent=False)
                return True
            if subtype_lower == "reconnected":
                self.set("waiting", "Network recovered: reconnected", is_subagent=False)
                return True

        if event_lower == "retry":
            attempt_raw = event.get("attempt")
            attempt = ""
            if isinstance(attempt_raw, int) and attempt_raw > 0:
                attempt = f" (attempt {attempt_raw})"
            if subtype_lower == "starting":
                self.set("network_problem", f"Network problems: retry starting{attempt}", is_subagent=False)
                return True
            if subtype_lower == "resuming":
                self.set("network_problem", f"Network problems: retry resuming{attempt}", is_subagent=False)
                return True

        return False
