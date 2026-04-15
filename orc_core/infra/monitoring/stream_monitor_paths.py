#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path resolution for StreamJsonMonitor — resolves task/runtime/stats/metrics paths from env overrides."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from ...persistence.runtime_state import runtime_state_path
from ...persistence.state_paths import active_task_path, metrics_path, stats_path


@dataclass(frozen=True)
class StreamMonitorPaths:
    task_state: Path
    task_runtime_state: Path
    stats: Path
    metrics: Path

    @classmethod
    def resolve(cls, workdir: str, child_env: Optional[Mapping[str, str]] = None) -> "StreamMonitorPaths":
        env = {str(k): str(v) for k, v in (child_env or {}).items()}

        task_state_override = env.get("ORC_TASK_FILE", "").strip()
        task_state = Path(task_state_override) if task_state_override else active_task_path(workdir)

        runtime_override = env.get("ORC_TASK_RUNTIME_FILE", "").strip()
        task_runtime_state = Path(runtime_override) if runtime_override else runtime_state_path(task_state)

        stats_override = env.get("ORC_STATS_FILE", "").strip()
        stats = Path(stats_override) if stats_override else stats_path(workdir)

        metrics_override = env.get("ORC_METRICS_FILE", "").strip()
        metrics = Path(metrics_override) if metrics_override else metrics_path(workdir)

        return cls(task_state=task_state, task_runtime_state=task_runtime_state, stats=stats, metrics=metrics)
