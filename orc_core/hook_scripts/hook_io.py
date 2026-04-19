#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File-I/O primitives for ORC hook scripts.

Hooks run out-of-process in user workspaces. Everything here is pure stdlib
plus `orc_core.infra.io` (state paths + atomic writes) — no imports from
`orc_core.board`, `orc_core.tasks`, or `orc_core.agents`.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from orc_core.infra.io.atomic_io import write_json_atomic
from orc_core.infra.io.state_paths import (
    artifacts_dir as external_artifacts_dir,
    metrics_path as external_metrics_path,
    stats_path as external_stats_path,
)

LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"

_BACKLOG_CHECKBOX_RE = re.compile(
    r"^\s*[-+*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$",
)
_TASK_ID_RE = re.compile(r"\bTASK-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_event(path: Path, level: str, message: str, **fields) -> None:
    min_level = LOG_LEVELS.get(
        os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip(),
        LOG_LEVELS[DEFAULT_LOG_LEVEL],
    )
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": now_iso(), "level": level, "message": message, **fields}
    with path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: dict) -> None:
    write_json_atomic(path, payload, ensure_ascii=False, indent=2)


def resolve_runtime_task_file(task_file: Path) -> Path:
    env_runtime_file = str(os.environ.get("ORC_TASK_RUNTIME_FILE") or "").strip()
    if env_runtime_file:
        return Path(env_runtime_file)
    return task_file.with_name("orc-task-runtime.json")


def read_task_active_seconds(runtime_task_file: Path, expected_task_id: str) -> float:
    payload = read_json(runtime_task_file, {})
    if not isinstance(payload, dict):
        return 0.0
    runtime_task_id = str(payload.get("task_id") or "").strip()
    if expected_task_id and runtime_task_id and runtime_task_id != expected_task_id:
        return 0.0
    try:
        return max(float(payload.get("active_seconds") or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def read_task_tokens(repo_root: Path) -> Optional[int]:
    env_metrics_path = str(os.environ.get("ORC_METRICS_FILE") or "").strip()
    metrics_path = Path(env_metrics_path) if env_metrics_path else external_metrics_path(str(repo_root))
    data = read_json(metrics_path, {})
    tokens = data.get("tokens_total")
    if isinstance(tokens, (int, float)):
        return int(tokens)
    return None


def load_stats(repo_root: Path) -> Dict[str, object]:
    env_stats_path = str(os.environ.get("ORC_STATS_FILE") or "").strip()
    stats_path = Path(env_stats_path) if env_stats_path else external_stats_path(str(repo_root))
    data = read_json(stats_path, {})
    data.setdefault("created_at", now_iso())
    data.setdefault("started_at", data.get("started_at") or "")
    data.setdefault("tokens_total", int(data.get("tokens_total") or 0))
    data.setdefault("tokens_by_task", data.get("tokens_by_task") or {})
    data.setdefault("durations_by_task", data.get("durations_by_task") or {})
    data.setdefault("recent_durations", data.get("recent_durations") or [])
    data.setdefault("active_seconds_total", float(data.get("active_seconds_total") or 0.0))
    return data


def save_stats(repo_root: Path, stats: Dict[str, object]) -> None:
    env_stats_path = str(os.environ.get("ORC_STATS_FILE") or "").strip()
    stats_path = Path(env_stats_path) if env_stats_path else external_stats_path(str(repo_root))
    write_json(stats_path, stats)


def parse_backlog_counts(path: Path) -> Tuple[int, int]:
    """Count total/done tasks in a backlog markdown file.

    Minimal stdlib parser — intentionally does not share `orc_core.board`'s
    markdown-it-py based parser to keep hook scripts isolated from domain
    modules. Matches `- [x] TASK-FOO description` checkbox items.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return 0, 0
    total = 0
    done = 0
    for line in text.splitlines():
        match = _BACKLOG_CHECKBOX_RE.match(line)
        if not match:
            continue
        if not _TASK_ID_RE.search(match.group("text")):
            continue
        total += 1
        if match.group("mark").lower() == "x":
            done += 1
    return total, done


def normalize_path(raw: object, cwd: object = "") -> Path:
    text = str(raw or "").strip()
    base = Path(str(cwd or "").strip() or os.getcwd())
    if not text:
        return base.resolve()
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        return candidate.resolve()
    except Exception:
        return candidate


def is_path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except Exception:
        return False


def artifacts_dir(base_workspace: object) -> Path:
    return external_artifacts_dir(str(base_workspace or ""))


def is_artifact_path(path: object, base_workspace: object, cwd: object = "") -> bool:
    candidate = normalize_path(path, cwd)
    return is_path_within(candidate, artifacts_dir(base_workspace))


def extract_applypatch_paths(patch_text: object) -> list[str]:
    text = str(patch_text or "")
    if not text:
        return []
    pattern = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$", re.MULTILINE)
    return [match.strip() for match in pattern.findall(text) if str(match).strip()]
