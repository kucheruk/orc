#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""StreamEventDispatcher — owns stream-JSON event parsing, stderr tracking, and state mutation.

Extracted from StreamJsonMonitor to isolate the event-processing responsibility from process
lifecycle, path resolution, and periodic reporting.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, Optional

from ...infra.io.logging import log_event, now_ms
from ...infra.io.timeline import timeline_instant
from .agent_output_sink import AgentOutputSink
from .conversation_persister import ConversationIdPersister
from .stream_monitor_state import StreamMonitorState
from .stream_parser import is_followup_prompt_event, parse_stream_line


class StreamEventDispatcher:
    """Handles stdout/stderr callbacks and dispatches parsed events into StreamMonitorState."""

    def __init__(
        self,
        state: StreamMonitorState,
        output_sink: AgentOutputSink,
        conversation_persister: ConversationIdPersister,
        log_path: Path,
        task_id: str,
        timeline_id: str,
        attempt: int,
        started_at: float,
        snapshot_publisher: Callable[[], None],
    ) -> None:
        self._state = state
        self._output_sink = output_sink
        self._conversation_persister = conversation_persister
        self._log_path = log_path
        self._task_id = task_id
        self._timeline_id = timeline_id
        self._attempt = attempt
        self._started_at = started_at
        self._publish_snapshot = snapshot_publisher
        self._first_output_recorded = False

        # Public event-derived attributes (preserved from the monolithic monitor).
        self.stderr_count: int = 0
        self.last_stderr_line: str = ""
        self.status_only_reports: int = 0
        self.ui_followup_prompt: bool = False
        self.result_status: Optional[str] = None
        self.result_seen_at: Optional[float] = None

    # ── Stream callbacks (called from AgentProcess reader thread) ─

    def on_stdout_line(self, decoded: str) -> None:
        self._output_sink.append("stdout", decoded)
        event = parse_stream_line(decoded, log_path=self._log_path)
        if event is not None:
            self.record_event(event)

    def on_stderr_line(self, decoded: str) -> None:
        self._output_sink.append("stderr", decoded)
        raw = decoded.strip()
        if not raw:
            return
        self.last_stderr_line = raw[:500]
        self.stderr_count += 1
        log_event(self._log_path, "WARN", "agent_stderr", line=self.last_stderr_line)

    # ── Event processing ────────────────────────────────────────

    def record_event(self, event: Dict[str, object]) -> None:
        if not self._first_output_recorded:
            self._first_output_recorded = True
            timeline_instant(
                timeline_id=self._timeline_id,
                task_id=self._task_id,
                step="first_meaningful_output",
                location="orc_core/stream_monitor.py:StreamJsonMonitor._record_event",
                attempt=self._attempt,
                result="received",
                data={"latency_ms": max(now_ms() - int(self._started_at * 1000), 0)},
            )
        had_session_id = self._state.session_id is not None
        event_type, subtype, raw = self._state.record_event(event)
        if not had_session_id and self._state.session_id is not None:
            self._conversation_persister.persist(self._state.session_id)
        if event_type == "result":
            status = subtype or str(event.get("status") or "")
            self.result_status = status.lower() if status else "success"
            self.result_seen_at = time.time()
        if is_followup_prompt_event(event_type, subtype, raw):
            self.ui_followup_prompt = True
        log_event(self._log_path, "INFO", "stream_json_event", event_type=event_type, subtype=subtype, size=len(raw))
        self._publish_snapshot()
