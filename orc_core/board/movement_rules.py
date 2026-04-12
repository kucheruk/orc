#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Movement rules for deferred card transitions — extensible registry."""

from __future__ import annotations

from .kanban_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_HANDOFF,
    STAGE_REVIEW,
    STAGE_TESTING,
)

# (current_stage, action) → target_stage
# Add new rules here without modifying KanbanBoard.
DEFERRED_MOVE_RULES: dict[tuple[str, str], str] = {
    (STAGE_TESTING, "Integrating"): STAGE_HANDOFF,
    (STAGE_HANDOFF, "Done"): STAGE_DONE,
    (STAGE_CODING, "Reviewing"): STAGE_REVIEW,
    (STAGE_REVIEW, "Testing"): STAGE_TESTING,
    # Integrator reject paths
    (STAGE_HANDOFF, "Reviewing"): STAGE_REVIEW,
    (STAGE_HANDOFF, "Testing"): STAGE_TESTING,
    # Tester/reviewer bounce-back
    (STAGE_TESTING, "Coding"): STAGE_CODING,
    (STAGE_REVIEW, "Coding"): STAGE_CODING,
}


def resolve_deferred_target(stage: str, action: str) -> str | None:
    """Return the target stage for a deferred move, or None if no rule matches."""
    return DEFERRED_MOVE_RULES.get((stage, action))
