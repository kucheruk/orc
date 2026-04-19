#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure stats/report formatting for hook scripts.

No I/O, no subprocess — takes a stats dict and returns a new one (or a
rendered report). Split from `hook_io` so report shape and throughput/ETA
math can evolve without touching the file layer.
"""
from __future__ import annotations

from typing import Dict, Optional

from .hook_io import now_iso

ETA_WINDOW_SIZE = 3


def ensure_started(stats: Dict[str, object], done_tasks: int) -> Dict[str, object]:
    if not stats.get("started_at"):
        stats["started_at"] = now_iso()
        stats["start_done"] = int(done_tasks)
    if "start_done" not in stats:
        stats["start_done"] = int(done_tasks)
    else:
        stats["start_done"] = int(stats.get("start_done") or 0)
    return stats


def update_tokens(stats: Dict[str, object], task_id: str, task_tokens: Optional[int]) -> Dict[str, object]:
    """No-op: token tracking is handled by ORC's `_update_completion_stats`.

    Hook must NOT write tokens — ORC process is the single source of truth
    for token accounting. Writing here would double-count because both the
    hook and ORC independently read the same metrics file.
    """
    return stats


def record_task_duration(stats: Dict[str, object], task_id: str, duration_seconds: float) -> Dict[str, object]:
    task_key = str(task_id or "").strip()
    if not task_key:
        return stats
    durations_by_task = stats.setdefault("durations_by_task", {})
    if task_key in durations_by_task:
        return stats
    duration_int = max(int(duration_seconds), 0)
    durations_by_task[task_key] = duration_int
    recent = stats.setdefault("recent_durations", [])
    if not isinstance(recent, list):
        recent = []
        stats["recent_durations"] = recent
    recent.append(duration_int)
    stats["recent_durations"] = recent[-ETA_WINDOW_SIZE:]
    stats["active_seconds_total"] = float(stats.get("active_seconds_total") or 0.0) + float(duration_int)
    return stats


def format_duration(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def build_report(stats: Dict[str, object], total_tasks: int, done_tasks: int) -> Dict[str, object]:
    stats = ensure_started(stats, done_tasks)
    active_seconds_total = max(float(stats.get("active_seconds_total") or 0.0), 0.0)
    minutes = max(active_seconds_total / 60.0, 0.001)
    tokens_total = int(stats.get("tokens_total") or 0)
    tokens_per_min = tokens_total / minutes
    recent_raw = stats.get("recent_durations") or []
    recent = [max(int(value), 0) for value in recent_raw if isinstance(value, (int, float)) and value > 0]
    window = recent[-ETA_WINDOW_SIZE:]
    average_task_seconds = (sum(window) / len(window)) if window else 0.0
    tasks_per_hour = (3600.0 / average_task_seconds) if average_task_seconds > 0 else 0.0
    remaining = max(total_tasks - done_tasks, 0)
    eta = "unknown"
    if average_task_seconds > 0:
        eta = format_duration(average_task_seconds * remaining)
    return {
        "running_time": format_duration(active_seconds_total),
        "tokens_total": tokens_total,
        "tokens_per_min": tokens_per_min,
        "tasks_per_hour": tasks_per_hour,
        "eta": eta,
        "tasks_remaining": remaining,
    }


def format_report(report: Dict[str, object]) -> str:
    return "\n".join(
        [
            f"running_time={report['running_time']}",
            f"tokens_total={report['tokens_total']}",
            f"tokens_per_min={report['tokens_per_min']:.1f}",
            f"tasks_per_hour={report['tasks_per_hour']:.2f}",
            f"eta={report['eta']}",
            f"tasks_remaining={report['tasks_remaining']}",
        ]
    )
