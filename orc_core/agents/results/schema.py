#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schema v1 for structured kanban agent results."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PAYLOAD_CARD_UPDATE = "card_update"
PAYLOAD_TEAMLEAD_ACTIONS = "teamlead_actions"
PAYLOAD_INCIDENT_TRIAGE = "incident_triage"
VALID_PAYLOAD_KINDS = frozenset({
    PAYLOAD_CARD_UPDATE,
    PAYLOAD_TEAMLEAD_ACTIONS,
    PAYLOAD_INCIDENT_TRIAGE,
})


@dataclass(frozen=True)
class LaunchFingerprint:
    stage: str
    action: str
    file_path: str
    state_version: int


@dataclass(frozen=True)
class CardUpdatePayload:
    task_id: str
    launch_fingerprint: LaunchFingerprint
    next_action: str = ""
    field_updates: dict[str, Any] = field(default_factory=dict)
    section_updates: dict[str, str] = field(default_factory=dict)
    feedback_append: str = ""


@dataclass(frozen=True)
class TeamleadActionPayload:
    type: str
    params: dict[str, Any]
    reason: str = ""


@dataclass(frozen=True)
class TeamleadActionsPayload:
    actions: list[TeamleadActionPayload] = field(default_factory=list)


@dataclass(frozen=True)
class IncidentTriagePayload:
    classification: str
    target_role: str
    fix_title: str
    body: str


@dataclass(frozen=True)
class StructuredAgentResultV1:
    payload_kind: str
    role: str
    run_id: str
    summary: str
    payload: CardUpdatePayload | TeamleadActionsPayload | IncidentTriagePayload
    schema_version: int = 1


def load_structured_agent_result(path: Path) -> StructuredAgentResultV1:
    return parse_structured_agent_result(json.loads(path.read_text(encoding="utf-8")))


def parse_structured_agent_result(data: Any) -> StructuredAgentResultV1:
    if not isinstance(data, dict):
        raise ValueError("Structured result must be a JSON object")
    schema_version = int(data.get("schema_version", 0))
    if schema_version != 1:
        raise ValueError(f"Unsupported schema_version: {schema_version}")
    payload_kind = _required_text(data, "payload_kind")
    if payload_kind not in VALID_PAYLOAD_KINDS:
        raise ValueError(f"Unsupported payload_kind: {payload_kind}")
    role = _required_text(data, "role")
    run_id = _required_text(data, "run_id")
    summary = str(data.get("summary", "") or "").strip()
    payload_raw = data.get("payload")
    if payload_kind == PAYLOAD_CARD_UPDATE:
        payload = _parse_card_update_payload(payload_raw)
    elif payload_kind == PAYLOAD_TEAMLEAD_ACTIONS:
        payload = _parse_teamlead_actions_payload(payload_raw)
    else:
        payload = _parse_incident_triage_payload(payload_raw)
    return StructuredAgentResultV1(
        schema_version=schema_version,
        payload_kind=payload_kind,
        role=role,
        run_id=run_id,
        summary=summary,
        payload=payload,
    )


def validate_structured_agent_result(
    result: StructuredAgentResultV1,
    *,
    expected_run_id: str = "",
    expected_role: str = "",
    expected_payload_kind: str = "",
) -> None:
    if expected_run_id and result.run_id != expected_run_id:
        raise ValueError(f"Unexpected run_id: {result.run_id}")
    if expected_role and result.role != expected_role:
        raise ValueError(f"Unexpected role: {result.role}")
    if expected_payload_kind and result.payload_kind != expected_payload_kind:
        raise ValueError(f"Unexpected payload_kind: {result.payload_kind}")


def _parse_card_update_payload(payload_raw: Any) -> CardUpdatePayload:
    payload = _require_mapping(payload_raw, "payload")
    fp = _require_mapping(payload.get("launch_fingerprint"), "launch_fingerprint")
    return CardUpdatePayload(
        task_id=_required_text(payload, "task_id"),
        launch_fingerprint=LaunchFingerprint(
            stage=_required_text(fp, "stage"),
            action=_required_text(fp, "action"),
            file_path=_required_text(fp, "file_path"),
            state_version=int(fp.get("state_version", 0)),
        ),
        next_action=str(payload.get("next_action", "") or "").strip(),
        field_updates=_dict_or_empty(payload.get("field_updates"), "field_updates"),
        section_updates=_string_dict_or_empty(payload.get("section_updates"), "section_updates"),
        feedback_append=str(payload.get("feedback_append", "") or "").strip(),
    )


def _parse_teamlead_actions_payload(payload_raw: Any) -> TeamleadActionsPayload:
    payload = _require_mapping(payload_raw, "payload")
    raw_actions = payload.get("actions", [])
    if not isinstance(raw_actions, list):
        raise ValueError("actions must be a list")
    actions: list[TeamleadActionPayload] = []
    for index, raw in enumerate(raw_actions):
        action = _require_mapping(raw, f"actions[{index}]")
        reason = str(action.get("reason", "") or "").strip()
        params = {k: v for k, v in action.items() if k not in {"type", "reason"}}
        actions.append(TeamleadActionPayload(
            type=_required_text(action, "type"),
            params=params,
            reason=reason,
        ))
    return TeamleadActionsPayload(actions=actions)


def _parse_incident_triage_payload(payload_raw: Any) -> IncidentTriagePayload:
    payload = _require_mapping(payload_raw, "payload")
    classification = _required_text(payload, "classification").lower()
    if classification not in {"project", "orc"}:
        raise ValueError(f"Invalid incident classification: {classification}")
    return IncidentTriagePayload(
        classification=classification,
        target_role=_required_text(payload, "target_role").lower(),
        fix_title=_required_text(payload, "fix_title"),
        body=_required_text(payload, "body"),
    )


def _required_text(data: dict[str, Any], key: str) -> str:
    value = str(data.get(key, "") or "").strip()
    if not value:
        raise ValueError(f"Missing required field: {key}")
    return value


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _dict_or_empty(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _string_dict_or_empty(value: Any, label: str) -> dict[str, str]:
    raw = _dict_or_empty(value, label)
    return {str(key): str(val or "") for key, val in raw.items()}
