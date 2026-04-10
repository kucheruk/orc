#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse agent output card, validate transitions, apply changes to the board."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .kanban_card import PROTECTED_FIELDS, KanbanCard, read_card, validate_card
from .kanban_constants import STAGE_ORDER, Action

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard

_logger = logging.getLogger(__name__)

# Fields that specific roles must NOT modify (role-based restrictions).
# These are not globally protected but belong to another role's responsibility.
_ROLE_READONLY_FIELDS: dict[str, frozenset[str]] = {
    "architect": frozenset({"value_score", "class_of_service", "cos_justification", "deadline"}),
    "coder": frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
    "reviewer": frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
    "tester": frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
    "integrator": frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
}

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
        "Arbitration": {Action.CODING, Action.REVIEWING, Action.TESTING, Action.BLOCKED, Action.PRODUCT, Action.ARCHITECT},
        "Blocked": {Action.CODING, Action.REVIEWING, Action.TESTING, Action.PRODUCT, Action.ARCHITECT},
    },
}

# Which action transitions require incrementing loop_count
_LOOP_BACK_ACTIONS: frozenset[str] = frozenset({Action.CODING})

# Stage the card should move to when action changes (if any)
_FORWARD_MOVES: dict[tuple[str, str], str] = {
    # (current_stage, new_action) → new_stage
    ("1_Inbox", Action.ARCHITECT): "2_Estimate",
    ("1_Inbox", Action.CODING): "3_Todo",           # product fast-tracks to backlog
    ("2_Estimate", Action.CODING): "3_Todo",
    ("4_Coding", Action.REVIEWING): "5_Review",
    ("5_Review", Action.TESTING): "6_Testing",       # reviewer approves for testing
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
    with board.card_lock(card.id):
        file_path = card.file_path
        if file_path is None or not file_path.exists():
            # Card may have been moved by another agent/teamlead while this agent was running.
            # Search by ID across all stage directories.
            found = board.find_card_file(card.id)
            if found is None:
                return [f"Card file not found (checked all stages): {card.id}"]
            _logger.info("Card %s moved during execution: %s → %s", card.id, file_path, found)
            file_path = found
            card.file_path = found

        updated = read_card(file_path)
        errors = _validate_agent_changes(card, updated, role)
        if errors:
            _logger.warning("Agent output validation errors for %s: %s", card.id, errors)
            return errors

        card_errors = validate_card(updated)
        if card_errors:
            _logger.warning("Card validation errors for %s: %s", card.id, card_errors)
            return card_errors

        # Auto-default: if the agent didn't change the action, apply the most
        # common "done" transition for that role so work keeps flowing.
        _IDENTITY_DEFAULTS: dict[str, dict[str, str]] = {
            "coder": {Action.CODING: Action.REVIEWING},
            "reviewer": {Action.REVIEWING: Action.TESTING},
            "tester": {Action.TESTING: Action.INTEGRATING},
        }
        if updated.action == card.action:
            defaults = _IDENTITY_DEFAULTS.get(role, {})
            default_next = defaults.get(card.action)
            if default_next:
                _logger.info(
                    "Agent %s left action unchanged (%s); auto-defaulting to %s for %s",
                    role, card.action, default_next, card.id,
                )
                updated.action = default_next

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
        # Block promotion to Todo/Coding if dependencies are unmet
        if new_stage in ("3_Todo", "4_Coding") and board.has_unmet_dependencies(updated):
            _logger.info("Cannot move %s to %s: unmet dependencies, staying in %s",
                          updated.id, new_stage, card.stage)
        elif new_stage and board.has_wip_room(new_stage):
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

    # Check role-based readonly fields — revert silently (same as protected fields)
    readonly = _ROLE_READONLY_FIELDS.get(role, frozenset())
    for field in readonly:
        orig_val = getattr(original, field)
        new_val = getattr(updated, field)
        if new_val != orig_val:
            _logger.info("Agent %s changed readonly field %s for %s (reverting)", role, field, original.id)
            setattr(updated, field, orig_val)

    # Validate action transition (identity = agent didn't change action, allowed)
    if updated.action != original.action:
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
