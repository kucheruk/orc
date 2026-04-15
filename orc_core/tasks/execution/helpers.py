#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone helper functions extracted from task_execution.py."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ...infra.io.atomic_io import write_json_atomic
from ...log import log_event
from .config import ETA_WINDOW_SIZE
from .request import TaskExecutionRequest
from .stage import TaskStageSpec


def _update_completion_stats(
    *,
    monitor,
    task_id: str,
    task_path: Path,
    workdir: str,
    log_path: Path,
) -> None:
    """Record token usage and task duration in stats file (replaces stop hook stats logic)."""
    from ...infra.io.state_paths import stats_path as get_stats_path
    from ..task_state import read_task_active_seconds

    stats_file = get_stats_path(workdir)
    try:
        stats = json.loads(stats_file.read_text(encoding="utf-8")) if stats_file.exists() else {}
    except (OSError, json.JSONDecodeError, ValueError):
        stats = {}
    stats.setdefault("tokens_total", 0)
    stats.setdefault("tokens_by_task", {})
    stats.setdefault("durations_by_task", {})
    stats.setdefault("recent_durations", [])
    stats.setdefault("active_seconds_total", 0.0)

    # Tokens
    task_tokens = monitor.metrics.tokens_total
    if task_tokens is not None and task_id and task_id not in stats["tokens_by_task"]:
        stats["tokens_by_task"][task_id] = int(task_tokens)
        stats["tokens_total"] = int(stats["tokens_total"]) + int(task_tokens)

    # Duration
    duration = read_task_active_seconds(task_path, expected_task_id=task_id)
    if duration > 0 and task_id and task_id not in stats["durations_by_task"]:
        duration_int = max(int(duration), 0)
        stats["durations_by_task"][task_id] = duration_int
        recent = stats.get("recent_durations") or []
        if not isinstance(recent, list):
            recent = []
        recent.append(duration_int)
        stats["recent_durations"] = recent[-ETA_WINDOW_SIZE:]
        stats["active_seconds_total"] = float(stats.get("active_seconds_total", 0)) + float(duration_int)

    try:
        write_json_atomic(stats_file, stats, ensure_ascii=False, indent=2)
    except Exception as exc:
        log_event(log_path, "WARN", "failed to update completion stats", error=str(exc))


def _restart_backoff_seconds(restart_count: int) -> float:
    # Deterministic capped backoff prevents rapid restart storms.
    return float(min(2 ** max(restart_count - 1, 0), 30))


def _write_prompt_file(run_root: Path, prompt: str, tag: str) -> Path:
    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{tag}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _build_agent_output_log_path(run_root: Path, task_id: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(task_id or "task"))[:80] or "task"
    return str(run_root / "raw-stream" / f"{stamp}__{safe_task_id}.log")


def _resolve_runtime_backlog_path(request: TaskExecutionRequest) -> Path:
    raw_arg = str(request.backlog_arg or "").strip()
    if not raw_arg:
        return request.backlog_path
    candidate = Path(raw_arg)
    if candidate.is_absolute():
        return candidate
    return Path(request.workdir) / candidate


def _sync_done_task_from_runtime_to_base(
    *,
    task_id: str,
    base_backlog_path: Path,
    runtime_backlog_path: Path,
    log_path: Path,
) -> bool:
    if runtime_backlog_path == base_backlog_path:
        return True
    from ..task_source import MarkdownTaskSource

    try:
        base_source = MarkdownTaskSource(base_backlog_path)
        if base_source.is_task_done(task_id):
            return True
        runtime_source = MarkdownTaskSource(runtime_backlog_path)
        if not runtime_source.is_task_done(task_id):
            return False
        found = base_source.mark_task_done(task_id)
        if not found:
            log_event(
                log_path,
                "ERROR",
                "failed to sync done task from runtime backlog: task not found in base backlog",
                task_id=task_id,
                base_backlog_path=str(base_backlog_path),
                runtime_backlog_path=str(runtime_backlog_path),
            )
            return False
        synced = base_source.is_task_done(task_id)
        if synced:
            log_event(
                log_path,
                "INFO",
                "synced done task from runtime backlog into base backlog",
                task_id=task_id,
                base_backlog_path=str(base_backlog_path),
                runtime_backlog_path=str(runtime_backlog_path),
            )
        return synced
    except Exception as exc:
        log_event(
            log_path,
            "ERROR",
            "failed to sync done task from runtime backlog",
            task_id=task_id,
            base_backlog_path=str(base_backlog_path),
            runtime_backlog_path=str(runtime_backlog_path),
            error=str(exc),
        )
        return False


def _should_defer_base_backlog_sync_to_integration(
    *,
    integrate_to_main: bool,
    base_backlog_path: Path,
    runtime_backlog_path: Path,
) -> bool:
    if not integrate_to_main:
        return False
    return runtime_backlog_path != base_backlog_path


def _find_first_stage_index(stage_specs: list[TaskStageSpec], target_stage_id: str) -> Optional[int]:
    normalized_target = str(target_stage_id or "").strip().lower()
    for idx, stage_spec in enumerate(stage_specs):
        current_id = str(stage_spec.stage_id or "").strip().lower()
        if current_id == normalized_target:
            return idx
    return None


def _is_fragmented_summary_lines(lines: list[str]) -> bool:
    if len(lines) < 5:
        return False
    short_lines = sum(1 for line in lines if len(line) <= 12)
    return short_lines >= int(len(lines) * 0.7)


def _normalize_fragmented_summary_text(summary_text: str) -> str:
    lines = [line.strip() for line in (summary_text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    if not _is_fragmented_summary_lines(lines):
        return "\n".join(lines)
    merged = " ".join(lines)
    merged = re.sub(r"\s+([,.;:!?])", r"\1", merged)
    merged = re.sub(r"(\()\s+", r"\1", merged)
    merged = re.sub(r"\s+(\))", r"\1", merged)
    merged = re.sub(r"\s*/\s*", "/", merged)
    merged = re.sub(r"\s*-\s*", "-", merged)
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged


