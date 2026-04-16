#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified card state machine — single source of truth for all transitions.

Replaces the scattered definitions in:
- agent_output.py: _FORWARD_MOVES, _IDENTITY_DEFAULTS, _VALID_TRANSITIONS
- movement_rules.py: DEFERRED_MOVE_RULES

Every stage/action/role transition is declared once here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .action_constants import Action
from .stage_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_INBOX,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_TODO,
)


@dataclass(frozen=True)
class Transition:
    """A single allowed state change in the card lifecycle."""
    from_stage: str
    from_action: str
    to_action: str
    to_stage: str | None   # None = stay in current stage
    role: str              # who triggers this transition
    auto_default: bool     # apply if agent leaves action unchanged
    loop_back: bool        # increment loop_count when this fires


# ── Transition table ────────────────────────────────────────────
# Read as: "When a card is in from_stage with from_action,
# the agent in role can change action to to_action, which moves
# the card to to_stage."

TRANSITIONS: tuple[Transition, ...] = (
    # ── Product role ───────────────────────────────────────────
    Transition(STAGE_INBOX, Action.PRODUCT, Action.ARCHITECT, STAGE_ESTIMATE, "product", False, False),
    Transition(STAGE_INBOX, Action.PRODUCT, Action.CODING, STAGE_TODO, "product", False, False),

    # ── Architect role ─────────────────────────────────────────
    Transition(STAGE_ESTIMATE, Action.ARCHITECT, Action.PRODUCT, None, "architect", False, False),
    Transition(STAGE_ESTIMATE, Action.ARCHITECT, Action.CODING, STAGE_TODO, "architect", False, False),

    # ── Coder role ─────────────────────────────────────────────
    Transition(STAGE_CODING, Action.CODING, Action.REVIEWING, STAGE_REVIEW, "coder", True, False),
    Transition(STAGE_CODING, Action.CODING, Action.TESTING, STAGE_TESTING, "coder", False, False),
    Transition(STAGE_CODING, Action.ARBITRATION, Action.REVIEWING, STAGE_REVIEW, "coder", True, False),
    Transition(STAGE_CODING, Action.ARBITRATION, Action.TESTING, STAGE_TESTING, "coder", False, False),

    # ── Reviewer role ──────────────────────────────────────────
    Transition(STAGE_REVIEW, Action.REVIEWING, Action.TESTING, STAGE_TESTING, "reviewer", True, False),
    Transition(STAGE_REVIEW, Action.REVIEWING, Action.CODING, STAGE_CODING, "reviewer", False, True),

    # ── Tester role ────────────────────────────────────────────
    Transition(STAGE_TESTING, Action.TESTING, Action.INTEGRATING, STAGE_HANDOFF, "tester", True, False),
    Transition(STAGE_TESTING, Action.TESTING, Action.CODING, STAGE_CODING, "tester", False, True),
    Transition(STAGE_TESTING, Action.TESTING, Action.REVIEWING, STAGE_REVIEW, "tester", False, False),

    # ── Integrator role ────────────────────────────────────────
    Transition(STAGE_HANDOFF, Action.INTEGRATING, Action.DONE, STAGE_DONE, "integrator", True, False),
    Transition(STAGE_HANDOFF, Action.INTEGRATING, Action.REVIEWING, STAGE_REVIEW, "integrator", False, False),
    Transition(STAGE_HANDOFF, Action.INTEGRATING, Action.TESTING, STAGE_TESTING, "integrator", False, False),
    Transition(STAGE_HANDOFF, Action.INTEGRATING, Action.CODING, STAGE_CODING, "integrator", False, True),

    # ── Teamlead role ──────────────────────────────────────────
    Transition(None, Action.ARBITRATION, Action.CODING, None, "teamlead", False, False),   # type: ignore[arg-type]
    Transition(None, Action.ARBITRATION, Action.REVIEWING, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.ARBITRATION, Action.TESTING, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.ARBITRATION, Action.BLOCKED, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.ARBITRATION, Action.PRODUCT, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.ARBITRATION, Action.ARCHITECT, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.BLOCKED, Action.CODING, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.BLOCKED, Action.REVIEWING, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.BLOCKED, Action.TESTING, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.BLOCKED, Action.PRODUCT, None, "teamlead", False, False),  # type: ignore[arg-type]
    Transition(None, Action.BLOCKED, Action.ARCHITECT, None, "teamlead", False, False),  # type: ignore[arg-type]
)


# ── Derived lookups (computed once from TRANSITIONS) ───────────

def _build_valid_transitions() -> dict[str, dict[str, set[str]]]:
    """Build {role: {from_action: {to_action, ...}}} from TRANSITIONS."""
    result: dict[str, dict[str, set[str]]] = {}
    for t in TRANSITIONS:
        role_dict = result.setdefault(t.role, {})
        role_dict.setdefault(t.from_action, set()).add(t.to_action)
    return result


def _build_forward_moves() -> dict[tuple[str, str], str]:
    """Build {(from_stage, to_action): to_stage} for immediate transitions."""
    result: dict[tuple[str, str], str] = {}
    for t in TRANSITIONS:
        if t.from_stage is not None and t.to_stage is not None:
            key = (t.from_stage, t.to_action)
            result[key] = t.to_stage
    return result


def _build_identity_defaults() -> dict[str, dict[str, str]]:
    """Build {role: {from_action: to_action}} for auto-defaults."""
    result: dict[str, dict[str, str]] = {}
    for t in TRANSITIONS:
        if t.auto_default:
            role_dict = result.setdefault(t.role, {})
            role_dict[t.from_action] = t.to_action
    return result


def _build_loop_back_actions() -> frozenset[str]:
    """Actions that increment loop_count when transitioned to."""
    return frozenset(t.to_action for t in TRANSITIONS if t.loop_back)


def _build_role_placement() -> dict[str, tuple[str, str]]:
    """Build {role: (stage, action)} — where a role's cards normally live.

    Picks the first non-None from_stage per role as the canonical placement.
    Used by incident system to inject fix cards at the right stage.
    """
    result: dict[str, tuple[str, str]] = {}
    for t in TRANSITIONS:
        if t.role not in result and t.from_stage is not None:
            result[t.role] = (t.from_stage, t.from_action)
    return result


VALID_TRANSITIONS = _build_valid_transitions()
FORWARD_MOVES = _build_forward_moves()
IDENTITY_DEFAULTS = _build_identity_defaults()
LOOP_BACK_ACTIONS = _build_loop_back_actions()
ROLE_PLACEMENT = _build_role_placement()
