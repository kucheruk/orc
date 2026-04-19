#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SnapshotBuilder — builds MonitorSnapshot from StreamMonitorState and publishes it.

Owns the live-status marker dedup so timeline receives one instant per transition
(phase/status/active tool-call count/subagent flag), not one per snapshot tick.
"""

from __future__ import annotations

from typing import Callable, Optional

from ...infra.io.timeline import timeline_instant
from ...contracts.session import MonitorSnapshot
from .stream_monitor_state import StreamMonitorState


class SnapshotBuilder:
    def __init__(
        self,
        state: StreamMonitorState,
        publisher: Optional[Callable[[MonitorSnapshot], None]],
        *,
        timeline_id: str,
        task_id: str,
        attempt: int,
    ) -> None:
        self._state = state
        self._publisher = publisher
        self._timeline_id = timeline_id
        self._task_id = task_id
        self._attempt = attempt
        self._last_live_marker: tuple[str, str, int, bool] | None = None

    def publish(self) -> MonitorSnapshot:
        snapshot = self._state.build_snapshot()
        if self._publisher is not None:
            self._publisher(snapshot)
        return snapshot

    def emit_live_status_change(self, snapshot: MonitorSnapshot) -> None:
        marker = (
            str(getattr(snapshot, "live_phase", "")),
            str(getattr(snapshot, "live_status", "")),
            int(getattr(snapshot, "active_tool_call_count", 0)),
            bool(getattr(snapshot, "is_subagent_activity", False)),
        )
        if marker == self._last_live_marker:
            return
        self._last_live_marker = marker
        timeline_instant(
            timeline_id=self._timeline_id,
            task_id=self._task_id,
            step="live_status_update",
            location="orc_core/agents/monitoring/snapshot_builder.py:SnapshotBuilder.emit_live_status_change",
            attempt=self._attempt,
            result=marker[0],
            data={
                "status": marker[1],
                "active_tool_calls": marker[2],
                "is_subagent_activity": marker[3],
            },
        )
