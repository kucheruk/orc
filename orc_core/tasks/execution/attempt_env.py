#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-attempt agent env preparation for execution-layer runtime artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ...agents.results.io import (
    RESULT_FILE_ENV,
    RESULT_RUN_ID_ENV,
    RESULT_TAG_ENV,
    build_result_file_path,
    build_result_run_id,
)


def build_attempt_agent_env(
    base_env: Mapping[str, str] | None,
    *,
    run_root: Path,
    task_id: str,
    stage_id: str,
    attempt: int,
) -> dict[str, str]:
    env = dict(base_env or {})
    result_tag = str(env.get(RESULT_TAG_ENV) or "").strip() or stage_id
    result_file = build_result_file_path(
        run_root,
        task_id=task_id,
        stage_id=result_tag,
        attempt=attempt,
    )
    env[RESULT_FILE_ENV] = str(result_file)
    env[RESULT_RUN_ID_ENV] = build_result_run_id(
        task_id=task_id,
        stage_id=result_tag,
        attempt=attempt,
    )
    return env
