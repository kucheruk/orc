#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Periodic metrics collection: git stats, backlog progress, ETA, runtime state."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from ...models.task_types import Task

from ..io.atomic_io import write_json_atomic
from ..io.logging import log_event, now_ms
from .monitor_types import MetricsStore, MonitorSnapshot
from ..io.timeline import timeline_instant


class MonitorMetricsCollector:
    """Collects and persists metrics for a running agent monitor."""

    def __init__(
        self,
        *,
        task_id: str,
        workdir: str,
        log_path: Path,
        metrics: MetricsStore,
        task_state_path: Path,
        task_runtime_state_path: Path,
        stats_path: Path,
        metrics_path: Path,
        timeline_id: str,
        attempt: int,
        started_at: float,
        backlog_task_lister: Optional[Callable[[Path], List[Task]]] = None,
        git_diff_fn: Optional[Callable] = None,
    ) -> None:
        self._task_id = task_id
        self._workdir = workdir
        self._log_path = log_path
        self._metrics = metrics
        self._task_state_path = task_state_path
        self._task_runtime_state_path = task_runtime_state_path
        self._stats_path = stats_path
        self._metrics_path = metrics_path
        self._timeline_id = timeline_id
        self._attempt = attempt
        self._started_at = started_at
        self._backlog_task_lister = backlog_task_lister
        self._git_diff_fn = git_diff_fn
        self._run_id = f"{int(started_at)}-{task_id}"
        self._last_git_stats_time = 0.0

    def update_git_stats(self) -> None:
        if self._git_diff_fn is None:
            return

        started_ms = now_ms()
        unstaged = self._git_diff_fn(self._workdir, timeout=10.0)
        staged = self._git_diff_fn(self._workdir, cached=True, timeout=10.0)
        if unstaged is None and staged is None:
            timeline_instant(
                timeline_id=self._timeline_id, task_id=self._task_id,
                step="git_stats_update",
                location="orc_core/monitor_metrics_collector.py",
                attempt=self._attempt, result="skipped", reason="git_stats_unavailable",
                data={"duration_ms": max(now_ms() - started_ms, 0)},
            )
            return

        added = 0
        deleted = 0
        files: set[str] = set()
        for output in (unstaged or "", staged or ""):
            for line in output.splitlines():
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                try:
                    added += int(parts[0])
                except ValueError:
                    pass
                try:
                    deleted += int(parts[1])
                except ValueError:
                    pass
                path = parts[2].strip()
                if path:
                    files.add(path)
        self._metrics.git_added = added
        self._metrics.git_deleted = deleted
        files_changed = len(files)
        if files_changed:
            self._metrics.files_edited = files_changed
        timeline_instant(
            timeline_id=self._timeline_id, task_id=self._task_id,
            step="git_stats_update",
            location="orc_core/monitor_metrics_collector.py",
            attempt=self._attempt, result="updated",
            data={"duration_ms": max(now_ms() - started_ms, 0), "files_changed": files_changed},
        )

    def write_metrics_snapshot(self) -> None:
        try:
            payload = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "task_id": self._task_id,
                "tokens_total": self._metrics.tokens_total,
                "lines": self._metrics.total_lines,
                "commands": self._metrics.command_count,
                "files_edited": self._metrics.files_edited,
                "git_added": self._metrics.git_added,
                "git_deleted": self._metrics.git_deleted,
                "tokens_status": self._metrics.tokens_status,
                "tokens_source": self._metrics.tokens_source,
            }
            self._metrics_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(self._metrics_path, payload, ensure_ascii=False, indent=2)
        except Exception as exc:
            log_event(self._log_path, "ERROR", "metrics snapshot write failed", error=str(exc))

    def refresh_backlog_progress(self, state) -> None:
        """Update progress from backlog. `state` must have set_progress and _progress_in_progress."""
        backlog_path = Path(self._workdir) / "BACKLOG.md"
        if self._task_state_path.exists():
            try:
                payload = json.loads(self._task_state_path.read_text(encoding="utf-8"))
                candidate = str(payload.get("backlog_path") or "").strip()
                if candidate:
                    backlog_path = Path(candidate)
            except (OSError, json.JSONDecodeError, ValueError):
                pass
        if backlog_path.name == "_board" or backlog_path.is_dir():
            return
        if not backlog_path.exists():
            return
        if self._backlog_task_lister is None:
            return
        try:
            tasks = self._backlog_task_lister(backlog_path)
        except Exception as exc:
            log_event(self._log_path, "WARN", "backlog progress refresh failed", error=str(exc))
            return
        total = len(tasks)
        done = sum(1 for task in tasks if task.done)
        state.set_progress(done, total, state._progress_in_progress)

    def update_eta_forecast(self, state) -> None:
        """Update ETA on `state` (must have set_eta_seconds and build_snapshot)."""
        try:
            stats = json.loads(self._stats_path.read_text(encoding="utf-8")) if self._stats_path.exists() else {}
        except Exception as exc:
            log_event(self._log_path, "WARN", "eta forecast read failed", error=str(exc))
            state.set_eta_seconds(None)
            return
        raw_durations = stats.get("recent_durations") or []
        if not isinstance(raw_durations, list):
            state.set_eta_seconds(None)
            return
        durations = [int(value) for value in raw_durations if isinstance(value, (int, float)) and value > 0]
        if not durations:
            state.set_eta_seconds(None)
            return
        window = durations[-3:]
        avg_seconds = sum(window) / max(len(window), 1)
        snapshot = state.build_snapshot()
        remaining = max(snapshot.progress_remaining, 0)
        state.set_eta_seconds(avg_seconds * remaining if remaining > 0 else 0.0)

    def update_task_runtime_state(self) -> None:
        from ..state.runtime_state import init_runtime_payload, load_runtime_payload

        started_ms = now_ms()
        now = time.time()
        runtime_path = self._task_runtime_state_path
        payload = load_runtime_payload(runtime_path)
        if not payload:
            payload = init_runtime_payload(self._task_id)
        if not isinstance(payload, dict):
            return
        if str(payload.get("task_id") or "").strip() != self._task_id:
            return
        active_seconds = float(payload.get("active_seconds") or 0.0)
        last_heartbeat = float(payload.get("last_heartbeat_at") or now)
        run_id = str(payload.get("run_id") or "")
        if run_id == self._run_id:
            active_seconds += max(now - last_heartbeat, 0.0)
        payload["active_seconds"] = active_seconds
        payload["last_heartbeat_at"] = now
        payload["run_id"] = self._run_id
        try:
            write_json_atomic(runtime_path, payload, ensure_ascii=False, indent=2)
        except Exception as exc:
            log_event(self._log_path, "WARN", "task runtime heartbeat write failed", error=str(exc))
        timeline_instant(
            timeline_id=self._timeline_id, task_id=self._task_id,
            step="runtime_state_update",
            location="orc_core/monitor_metrics_collector.py",
            attempt=self._attempt, result="ok",
            data={"duration_ms": max(now_ms() - started_ms, 0)},
        )

    def maybe_update_git_stats(self, now: float) -> None:
        """Update git stats if 10+ seconds since last update."""
        if now - self._last_git_stats_time >= 10.0:
            self._last_git_stats_time = now
            self.update_git_stats()
