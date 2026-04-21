#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OrphanedToolCallFinalizer — clears live tool calls that never got a result.

Invoked when the agent process exits: asks StreamMonitorState to finalize any
still-open tool calls, logs/timelines the outcome, and republishes the snapshot.
"""

from __future__ import annotations

from pathlib import Path

from ...log import log_event
from ...infra.io.timeline import timeline_instant
from .snapshot_builder import SnapshotBuilder
from .stream_monitor_state import StreamMonitorState


class OrphanedToolCallFinalizer:
    def __init__(
        self,
        *,
        state: StreamMonitorState,
        snapshot_builder: SnapshotBuilder,
        log_path: Path,
        task_id: str,
        timeline_id: str,
        attempt: int,
    ) -> None:
        self._state = state
        self._snapshot_builder = snapshot_builder
        self._log_path = log_path
        self._task_id = task_id
        self._timeline_id = timeline_id
        self._attempt = attempt

    def handle_process_exit(self, reason: str) -> None:
        try:
            result = self._state.force_finalize_live_tool_calls(reason)
        except Exception as exc:
            log_event(self._log_path, "WARN", "forced_tool_close_failed", reason=reason, error=str(exc))
            return
        cleared = int(result.get("cleared") or 0)
        if cleared <= 0:
            return
        pending = result.get("pending")
        log_event(
            self._log_path, "WARN", "forced_tool_close",
            reason=str(result.get("reason") or reason),
            cleared=cleared,
            pending_preview=pending if isinstance(pending, list) else [],
        )
        timeline_instant(
            timeline_id=self._timeline_id,
            task_id=self._task_id,
            step="forced_tool_close",
            location="orc_core/agents/monitoring/orphan_tool_call_finalizer.py:OrphanedToolCallFinalizer.handle_process_exit",
            attempt=self._attempt,
            result="cleared",
            reason=str(result.get("reason") or reason),
            data={"cleared": cleared},
        )
        self._snapshot_builder.publish()
