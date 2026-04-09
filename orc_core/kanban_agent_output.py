#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse agent output card, validate transitions, apply changes to the board."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .kanban_card import PROTECTED_FIELDS, KanbanCard, read_card
from .kanban_constants import STAGE_ORDER, Action

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard

_logger = logging.getLogger(__name__)

# Valid action transitions per role
_VALID_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "product": {
        "Product": {Action.ARCHITECT, Action.CODING},  # Architect (new) or Coding (approved for backlog)
    },
    "architect": {
        "Architect": {Action.PRODUCT},         # Estimate → back to Product for prioritization
    },
    "coder": {
        "Coding": {Action.REVIEWING, Action.TESTING},
    },
    "reviewer": {
        "Reviewing": {Action.CODING, Action.TESTING},
    },
    "tester": {
        "Testing": {Action.CODING, Action.INTEGRATING},
    },
    "integrator": {
        "Integrating": {Action.DONE},
    },
    "teamlead": {
        "Arbitration": {Action.CODING, Action.REVIEWING, Action.TESTING, Action.BLOCKED},
        "Blocked": {Action.CODING, Action.REVIEWING, Action.TESTING},
    },
}

# Which action transitions require incrementing loop_count
_LOOP_BACK_ACTIONS: frozenset[str] = frozenset({Action.CODING})

# Stage the card should move to when action changes (if any)
_FORWARD_MOVES: dict[tuple[str, str], str] = {
    # (current_stage, new_action) → new_stage
    ("1_Inbox", Action.ARCHITECT): "2_Estimate",
    ("2_Estimate", Action.CODING): "3_Todo",
    ("4_Coding", Action.REVIEWING): "5_Review",
    ("5_Review", Action.TESTING): "6_Testing",
    ("6_Testing", Action.INTEGRATING): "7_Handoff",
    ("7_Handoff", Action.DONE): "8_Done",
}


def process_agent_result(
    board: "KanbanBoard",
    card: KanbanCard,
    role: str,
) -> list[str]:
    """Re-read card from disk (agent modified it), validate and apply transitions.

    Returns list of validation errors (empty = success).
    """
    if card.file_path is None or not card.file_path.exists():
        return [f"Card file not found: {card.file_path}"]

    updated = read_card(card.file_path)
    errors = _validate_agent_changes(card, updated, role)
    if errors:
        _logger.warning("Agent output validation errors for %s: %s", card.id, errors)
        return errors

    # Apply valid changes
    new_action = updated.action
    old_action = card.action

    # Detect loop-back (reviewer/tester sending back to coder)
    if new_action in _LOOP_BACK_ACTIONS and old_action != Action.CODING:
        updated.loop_count = card.loop_count + 1

    # Restore protected fields from original
    updated.stage = card.stage
    updated.roi = card.roi
    updated.assigned_agent = card.assigned_agent
    updated.created_at = card.created_at

    # Recompute ROI in case value/effort changed
    updated.refresh_roi()
    updated.touch()
    board.save_card(updated, old_action=old_action, role=role)

    # Move card if this transition requires a stage change
    move_key = (card.stage, new_action)
    new_stage = _FORWARD_MOVES.get(move_key)
    if new_stage and board.has_wip_room(new_stage):
        board.move_card(updated, new_stage, reason=f"{role}: {old_action} -> {new_action}")
        # Ensure action is Done when card reaches 8_Done
        if new_stage == "8_Done" and updated.action != Action.DONE:
            updated.action = Action.DONE
            board.save_card(updated)
    elif new_stage and not board.has_wip_room(new_stage):
        _logger.info("Cannot move %s to %s: WIP limit reached, will retry later", card.id, new_stage)

    # Sync the original card object and refresh board state
    _sync_card(card, updated)
    board.refresh()
    return []


def _validate_agent_changes(
    original: KanbanCard,
    updated: KanbanCard,
    role: str,
) -> list[str]:
    errors: list[str] = []

    # Check protected fields
    if updated.id != original.id:
        errors.append(f"Agent changed id from {original.id} to {updated.id}")

    # Validate action transition
    role_transitions = _VALID_TRANSITIONS.get(role, {})
    valid_actions = role_transitions.get(original.action, set())
    if valid_actions and updated.action not in valid_actions:
        errors.append(
            f"Invalid transition for {role}: {original.action} → {updated.action}. "
            f"Valid: {valid_actions}"
        )

    # Stage must not be changed by agent
    if updated.stage != original.stage:
        _logger.info("Agent changed stage for %s (will be overridden)", original.id)

    return errors


def _sync_card(target: KanbanCard, source: KanbanCard) -> None:
    for field in (
        "title", "action", "class_of_service", "cos_justification",
        "deadline", "value_score", "effort_score", "roi",
        "dependencies", "loop_count", "assigned_agent",
        "created_at", "updated_at", "body", "stage", "file_path",
    ):
        setattr(target, field, getattr(source, field))
