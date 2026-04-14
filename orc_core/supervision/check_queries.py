#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure-query helpers used by completion checks — no side effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

import psutil

from ..infra.process.process import is_pid_alive

if TYPE_CHECKING:
    from ..infra.monitoring.monitor_protocol import StreamMonitorProtocol


def _monitor_pid_missing(monitor: "StreamMonitorProtocol") -> bool:
    try:
        monitor.refresh_process_status()
    except Exception:
        pass
    if monitor.proc.poll() is not None:
        return False
    pid = monitor.proc.pid or monitor.init_pid
    if not isinstance(pid, int) or pid <= 0:
        return False
    return not is_pid_alive(pid)


def _is_model_unavailable_stderr(last_stderr_line: str) -> bool:
    normalized = str(last_stderr_line or "").strip().lower()
    if not normalized:
        return False
    markers = (
        "cannot use this model",
        "unknown model",
        "model not found",
        "invalid model",
    )
    return any(marker in normalized for marker in markers)


def _get_active_children_count(monitor: "StreamMonitorProtocol") -> int:
    pid = monitor.proc.pid or monitor.init_pid
    if not isinstance(pid, int) or pid <= 0:
        return 0
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return 0
    active_count = 0
    for child in children:
        try:
            if child.status() != psutil.STATUS_ZOMBIE:
                active_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            continue
    return active_count
