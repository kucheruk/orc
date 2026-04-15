#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Side-effecting reporters used by completion checks (logging, tool cleanup)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...log import log_event

if TYPE_CHECKING:
    from ...infra.monitoring.monitor_protocol import StreamMonitorProtocol


def _force_close_active_tools_if_needed(
    monitor: "StreamMonitorProtocol",
    log_path,
    task_id: str,
    reason: str,
) -> None:
    try:
        result = monitor.force_finalize_live_tool_calls(reason)
    except Exception as exc:
        log_event(log_path, "WARN", "force close tools failed", task_id=task_id, reason=reason, error=str(exc))
        return
    cleared = int(result.get("cleared") or 0)
    if cleared <= 0:
        return
    pending = result.get("pending")
    log_event(
        log_path,
        "WARN",
        "force closed active tools",
        task_id=task_id,
        reason=str(result.get("reason") or reason),
        cleared=cleared,
        pending_preview=pending if isinstance(pending, list) else [],
    )
