#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Result artifact path and run-id helpers."""

from __future__ import annotations

import re
from pathlib import Path

RESULT_FILE_ENV = "ORC_AGENT_RESULT_FILE"
RESULT_RUN_ID_ENV = "ORC_AGENT_RUN_ID"
RESULT_TAG_ENV = "ORC_AGENT_RESULT_TAG"


def build_result_run_id(*, task_id: str, stage_id: str, attempt: int) -> str:
    return f"{task_id}:{stage_id}:attempt-{attempt}"


def build_result_file_path(
    run_root: Path,
    *,
    task_id: str,
    stage_id: str,
    attempt: int,
) -> Path:
    results_dir = run_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    safe_task = _safe_segment(task_id)
    safe_stage = _safe_segment(stage_id)
    return results_dir / f"{safe_task}__{safe_stage}__attempt-{attempt}.json"


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return cleaned.strip("._") or "unknown"
