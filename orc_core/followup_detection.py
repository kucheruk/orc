#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple, Union

DEFAULT_STRUCTURED_SUBTYPES = (
    "user_input_requested",
    "input_requested",
    "waiting_for_input",
    "followup_prompt",
    "follow_up_prompt",
)

DEFAULT_RESULT_ERROR_STATUSES = (
    "error",
    "failed",
    "failure",
)

DEFAULT_TEXT_MARKERS = (
    "add a follow-up",
    "follow-up",
    "follow up",
    "need your input",
    "waiting for your input",
)

TRUTHY_INPUT_FLAGS = {
    "user_input_requested",
    "requires_user_input",
    "waiting_for_input",
    "awaiting_user_input",
    "input_needed",
    "needs_input",
}


@dataclass(frozen=True)
class FollowupDetectionConfig:
    structured_subtypes: Tuple[str, ...] = DEFAULT_STRUCTURED_SUBTYPES
    result_error_statuses: Tuple[str, ...] = DEFAULT_RESULT_ERROR_STATUSES
    text_markers: Tuple[str, ...] = DEFAULT_TEXT_MARKERS


def _normalize_items(values: Iterable[object]) -> Tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized and normalized not in result:
                result.append(normalized)
    return tuple(result)


def _config_from_json(payload: object) -> FollowupDetectionConfig:
    if not isinstance(payload, dict):
        return FollowupDetectionConfig()
    subtype_values = payload.get("structured_subtypes")
    status_values = payload.get("result_error_statuses")
    marker_values = payload.get("text_markers")
    structured_subtypes = _normalize_items(subtype_values if isinstance(subtype_values, list) else DEFAULT_STRUCTURED_SUBTYPES)
    result_error_statuses = _normalize_items(status_values if isinstance(status_values, list) else DEFAULT_RESULT_ERROR_STATUSES)
    text_markers = _normalize_items(marker_values if isinstance(marker_values, list) else DEFAULT_TEXT_MARKERS)
    return FollowupDetectionConfig(
        structured_subtypes=structured_subtypes or DEFAULT_STRUCTURED_SUBTYPES,
        result_error_statuses=result_error_statuses or DEFAULT_RESULT_ERROR_STATUSES,
        text_markers=text_markers or DEFAULT_TEXT_MARKERS,
    )


def load_followup_detection_config(workdir: Union[Path, str]) -> FollowupDetectionConfig:
    path = Path(workdir) / "followup_markers.json"
    if not path.exists():
        return FollowupDetectionConfig()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return FollowupDetectionConfig()
    return _config_from_json(payload)


def _iter_values(value: object):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key, inner
            yield from _iter_values(inner)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values(item)


def _has_truthy_input_flag(event: Dict[str, object]) -> bool:
    for key, value in _iter_values(event):
        if not isinstance(key, str):
            continue
        key_lower = key.strip().lower()
        if key_lower not in TRUTHY_INPUT_FLAGS:
            continue
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"true", "yes", "1", "requested"}:
            return True
    return False


def _is_structured_followup(event: Dict[str, object], config: FollowupDetectionConfig) -> bool:
    subtype = str(event.get("subtype") or "").strip().lower()
    if subtype and subtype in config.structured_subtypes:
        return True
    return _has_truthy_input_flag(event)


def _is_text_followup(event: Dict[str, object], raw: str, config: FollowupDetectionConfig) -> bool:
    event_type = str(event.get("type") or "").strip().lower()
    status = str(event.get("status") or event.get("subtype") or "").strip().lower()
    if event_type != "result":
        return False
    if status not in config.result_error_statuses:
        return False
    normalized = raw.lower()
    return any(marker in normalized for marker in config.text_markers)


def is_followup_prompt_event(event: Dict[str, object], raw: str, config: FollowupDetectionConfig) -> bool:
    if _is_structured_followup(event, config):
        return True
    return _is_text_followup(event, raw, config)
