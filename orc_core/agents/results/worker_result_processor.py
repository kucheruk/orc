#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Worker-side loading and application of structured card_update results."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ...tasks.completion.outcomes import TaskOutcomeTracker
from .card_update_apply import apply_card_update_result
from .schema import (
    PAYLOAD_CARD_UPDATE,
    CardUpdatePayload,
    LaunchFingerprint,
    StructuredAgentResultV1,
    load_structured_agent_result,
    validate_structured_agent_result,
)

_logger = logging.getLogger(__name__)


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
    result: StructuredAgentResultV1 | None = None
    if result_path is None:
        # Agent completed and the caller has already verified non-empty
        # delivery (verify_and_commit_uncommitted + _reject_empty_delivery
        # run before this function), so there IS work on the branch. The
        # only thing missing is the metadata JSON the agent was supposed
        # to write at $ORC_AGENT_RESULT_FILE. Cursor-agent's gpt-5.3-codex
        # intermittently skips that final write when it decides the
        # primary task (commit code) is done — each such skip would
        # otherwise discard the whole attempt and burn ~30–40k tokens of
        # real work. Synthesize a minimal card_update payload from
        # ORC's own knowledge and proceed.
        result = _synthesize_card_update_fallback(card, role, agent_run_id)
        _logger.warning(
            "Synthesized fallback card_update result for %s (agent did not "
            "write %s); advancing on committed delivery.",
            card.id, agent_result_file,
        )
    else:
        try:
            result = load_structured_agent_result(result_path)
            # Role and payload kind must match exactly; the attempt number in
            # run_id is intentionally NOT enforced — cursor-agent in --resume
            # mode keeps writing to its original attempt path even after ORC
            # increments the attempt counter, so we accept any attempt for
            # the same task/stage.
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
            # File exists but can't be parsed/validated — in practice this
            # is the heredoc JSON escape failing on a literal backtick,
            # newline, or control character that the agent embedded in
            # `implementation_notes`. Same trade-off as the missing-file
            # branch: the delivery is already committed on disk, so we
            # prefer advancing via synthesis over discarding 30–40k
            # tokens of real work for a metadata-escape bug.
            _logger.warning(
                "Malformed agent result at %s (%s) for %s — synthesizing "
                "fallback and advancing on committed delivery.",
                result_path, exc, card.id,
            )
            result = _synthesize_card_update_fallback(card, role, agent_run_id)

    if outcomes.has_applied_result(result.run_id):
        return []

    errors = apply_card_update_result(board, card, role, result)
    if errors:
        return errors
    outcomes.record_applied_result(result.run_id)
    return []


def _synthesize_card_update_fallback(
    card,
    role: str,
    agent_run_id: str,
) -> StructuredAgentResultV1:
    """Build a minimum-viable card_update payload for the current card state.

    Used when the agent terminated cleanly with non-empty delivery but did
    not write the result metadata file. All fields come from ORC's own
    view of the card — there is no new semantic information from the
    agent, and that is OK: the caller has already confirmed that the
    delivery is non-empty, so advancing the card through its default
    next-action path is the correct recovery.
    """
    fingerprint = LaunchFingerprint(
        stage=str(getattr(card, "stage", "") or ""),
        action=str(getattr(card, "action", "") or ""),
        file_path=str(getattr(card, "file_path", "") or ""),
        state_version=int(getattr(card, "state_version", 0) or 0),
    )
    payload = CardUpdatePayload(
        task_id=str(getattr(card, "id", "") or ""),
        launch_fingerprint=fingerprint,
        next_action="",  # empty triggers stage-based default in apply layer
        field_updates={},
        section_updates={},
        feedback_append="",
    )
    return StructuredAgentResultV1(
        payload_kind=PAYLOAD_CARD_UPDATE,
        role=role,
        run_id=agent_run_id,
        summary="Synthesized by ORC: agent delivered commits but did not "
                "write the structured result file; advancing via default "
                "stage transition.",
        payload=payload,
    )


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
