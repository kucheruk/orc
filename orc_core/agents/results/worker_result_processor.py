#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker-side loading and application of structured card_update results."""

from __future__ import annotations

from pathlib import Path

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
    if outcomes.has_applied_result(agent_run_id):
        return []

    result_path = Path(agent_result_file)
    if not result_path.exists():
        return [f"structured result file not found: {result_path}"]

    try:
        result = load_structured_agent_result(result_path)
        validate_structured_agent_result(
            result,
            expected_run_id=agent_run_id,
            expected_role=role,
            expected_payload_kind=PAYLOAD_CARD_UPDATE,
        )
    except Exception as exc:
        return [f"invalid structured result: {exc}"]

    errors = apply_card_update_result(board, card, role, result)
    if errors:
        return errors
    outcomes.record_applied_result(agent_run_id)
    return []
