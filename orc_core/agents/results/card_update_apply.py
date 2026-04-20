#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate and apply structured card_update results to canonical board state."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ...board.action_constants import Action
from ...board.card_sections import merge_section_updates
from ...board.state_machine import FORWARD_MOVES, IDENTITY_DEFAULTS, LOOP_BACK_ACTIONS, VALID_TRANSITIONS
from ...board.stage_constants import STAGE_CODING, STAGE_ORDER, STAGE_TODO
from .card_update_rules import allowed_fields, allowed_sections, can_append_feedback
from .schema import CardUpdatePayload, StructuredAgentResultV1

if TYPE_CHECKING:
    from ...board.kanban_board import KanbanBoard
    from ...board.kanban_card import KanbanCard

_logger = logging.getLogger(__name__)


def apply_card_update_result(
    board: "KanbanBoard",
    card: "KanbanCard",
    role: str,
    result: StructuredAgentResultV1,
) -> list[str]:
    payload = result.payload
    if not isinstance(payload, CardUpdatePayload):
        return ["structured result payload is not card_update"]
    with board.locked_card(card.id):
        current = board.card_by_id(card.id)
        if current is None:
            return [f"Card not found: {card.id}"]
        errors = _validate_card_update(current, payload, role, board=board)
        if errors:
            return errors

        old_action = current.action
        next_action = _resolve_next_action(current, payload, role)
        if next_action != old_action:
            current.action = next_action
        _apply_field_updates(current, payload.field_updates)
        current.body = merge_section_updates(
            current.body,
            section_updates=payload.section_updates,
            feedback_append=payload.feedback_append,
        )
        if current.action in LOOP_BACK_ACTIONS and old_action != Action.CODING:
            current.loop_count += 1
        current.refresh_roi()
        card_errors = current.validate()
        if card_errors:
            _logger.warning("Card validation warnings for %s: %s", current.id, card_errors)
        board.save_card(current, old_action=old_action, role=role)
        _apply_stage_change(board, current, old_action)
        board.refresh()
        return []


def _validate_card_update(card: "KanbanCard", payload: CardUpdatePayload, role: str, *, board: "KanbanBoard" = None) -> list[str]:
    errors: list[str] = []
    if payload.task_id != card.id:
        errors.append(f"result task_id {payload.task_id} does not match {card.id}")
    if payload.launch_fingerprint.stage != card.stage:
        errors.append("launch fingerprint stage is stale")
    if payload.launch_fingerprint.action != card.action:
        errors.append("launch fingerprint action is stale")
    # Prompts hand agents the relative form "tasks/{stage}/{id}.md"
    # (roles.py _build_prompt), so the fingerprint is compared against the
    # same canonical relative path rather than the card's absolute
    # file_path, which would always mismatch.
    expected_path = f"tasks/{card.stage}/{card.id}.md"
    agent_path = payload.launch_fingerprint.file_path.strip()
    if agent_path not in (expected_path, str(card.file_path)):
        errors.append("launch fingerprint file_path is stale")
    # state_version is intentionally NOT validated: save_card bumps it on
    # every non-semantic write (token-budget sync, teamlead feedback) and a
    # mismatch there would discard an otherwise-valid agent result. The
    # stage/action/file_path checks above already catch every transition
    # that would make the agent's payload stale.

    disallowed_fields = set(payload.field_updates) - set(allowed_fields(role))
    if disallowed_fields:
        errors.append(f"disallowed field_updates for {role}: {sorted(disallowed_fields)}")

    disallowed_sections = set(payload.section_updates) - set(allowed_sections(role))
    if disallowed_sections:
        errors.append(f"disallowed section_updates for {role}: {sorted(disallowed_sections)}")
    if "feedback_checklist" in payload.section_updates:
        errors.append("feedback_checklist must use feedback_append, not section_updates")
    if payload.feedback_append and not can_append_feedback(role):
        errors.append(f"{role} may not append feedback")

    next_action = payload.next_action.strip()
    if next_action:
        valid_actions = VALID_TRANSITIONS.get(role, {}).get(card.action, set())
        if valid_actions and next_action not in valid_actions:
            errors.append(f"invalid transition for {role}: {card.action} -> {next_action}")

        # Reject agent-driven transitions to Blocked when the card has
        # unmet dependencies — "waiting on deps" is a system-gated state
        # (pull strategies already refuse to pick up a card until its
        # deps are Done), not a human-gated one. An agent flipping such
        # a card to Blocked manufactures a false escalation: the human
        # reviewer cannot do anything except unblock and wait for the
        # same deps the system was already waiting on, and the card's
        # body accumulates Block-Reason paragraphs that burn tokens on
        # every subsequent agent invocation that reads it.
        #
        # The two cards caught by this on jeeves 2026-04-20 were
        # NOTIF-004-B (1_Inbox, deps NOTIF-004-A still in Coding) and
        # QA-003-A (2_Estimate, deps QA-001-C/QA-002-C still in
        # Estimate). Both were re-routed through the Blocked-sweep
        # human-review path even though there was nothing a human
        # could productively do.
        if next_action == Action.BLOCKED and board is not None and board.has_unmet_dependencies(card):
            errors.append(
                f"cannot set action=Blocked on {card.id}: card has unmet dependencies "
                "and is already system-gated; block is for human-actionable issues only"
            )
    return errors


def _resolve_next_action(card: "KanbanCard", payload: CardUpdatePayload, role: str) -> str:
    explicit = payload.next_action.strip()
    if explicit:
        return explicit
    default_next = IDENTITY_DEFAULTS.get(role, {}).get(card.action)
    return default_next or card.action


def _apply_field_updates(card: "KanbanCard", updates: dict[str, Any]) -> None:
    for field, value in updates.items():
        if field == "dependencies":
            setattr(card, field, _parse_dependencies(value))
            continue
        if field in {"value_score", "effort_score"}:
            setattr(card, field, int(value))
            continue
        setattr(card, field, str(value or ""))


def _parse_dependencies(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _apply_stage_change(board: "KanbanBoard", card: "KanbanCard", old_action: str) -> None:
    new_stage = FORWARD_MOVES.get((card.stage, card.action))
    if card.action == Action.DONE:
        return
    if new_stage in {STAGE_TODO, STAGE_CODING} and board.has_unmet_dependencies(card):
        return
    if new_stage and board.has_wip_room(new_stage):
        is_backward = STAGE_ORDER.get(new_stage, 0) < STAGE_ORDER.get(card.stage, 0)
        board.move_card(
            card,
            new_stage,
            allow_backward=is_backward,
            reason=f"structured_result: {old_action} -> {card.action}",
        )
