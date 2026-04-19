#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker-side loading and application of structured card_update results."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...tasks.completion.outcomes import TaskOutcomeTracker
from .card_update_apply import apply_card_update_result
from .schema import PAYLOAD_CARD_UPDATE, load_structured_agent_result, validate_structured_agent_result


def process_worker_card_result(
    board,
    card,
    role: str,
    *,
    agent_result_file: str,
    agent_run_id: str,
    outcomes: TaskOutcomeTracker,
) -> list[str]:
    if not agent_result_file:
        return ["missing structured result path"]
    if not agent_run_id:
        return ["missing structured result run_id"]

    result_path = _resolve_existing_result_path(Path(agent_result_file))
    if result_path is None:
        return [f"structured result file not found: {agent_result_file}"]

    try:
        result = load_structured_agent_result(result_path)
        # Role and payload kind must match exactly; the attempt number in run_id
        # is intentionally NOT enforced — cursor-agent in --resume mode keeps
        # writing to its original attempt path even after ORC increments the
        # attempt counter, so we accept any attempt for the same task/stage.
        validate_structured_agent_result(
            result,
            expected_role=role,
            expected_payload_kind=PAYLOAD_CARD_UPDATE,
        )
        expected_prefix = _run_id_task_stage_prefix(agent_run_id)
        actual_prefix = _run_id_task_stage_prefix(result.run_id)
        if expected_prefix and actual_prefix != expected_prefix:
            return [
                f"result run_id {result.run_id!r} does not match task/stage "
                f"{expected_prefix!r}"
            ]
        payload_task_id = getattr(result.payload, "task_id", "")
        if payload_task_id and payload_task_id != card.id:
            return [
                f"result task_id {payload_task_id!r} does not match card {card.id!r}"
            ]
    except Exception as exc:
        return [f"invalid structured result: {exc}"]

    if outcomes.has_applied_result(result.run_id):
        return []

    errors = apply_card_update_result(board, card, role, result)
    if errors:
        return errors
    outcomes.record_applied_result(result.run_id)
    return []


def _run_id_task_stage_prefix(run_id: str) -> str:
    """Return the "task:stage" prefix of a run_id, dropping the attempt suffix."""
    text = str(run_id or "").strip()
    if not text:
        return ""
    # run_id shape is "TASK:STAGE:attempt-N".
    last_sep = text.rfind(":")
    if last_sep < 0:
        return text
    tail = text[last_sep + 1 :]
    if not tail.startswith("attempt-"):
        return text
    return text[:last_sep]


def _resolve_existing_result_path(primary: Path) -> Optional[Path]:
    """If the expected attempt file is missing, fall back to any attempt for
    the same task+stage in the same results/ directory (newest mtime wins).
    """
    if primary.exists():
        return primary
    results_dir = primary.parent
    if not results_dir.exists():
        return None
    name = primary.name
    double_sep = name.rfind("__")
    if double_sep < 0:
        return None
    prefix = name[: double_sep + len("__")]  # "{safe_task}__{safe_stage}__"
    candidates = sorted(
        results_dir.glob(f"{prefix}attempt-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None
