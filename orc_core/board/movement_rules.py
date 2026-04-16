#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Movement rules for deferred card transitions — derived from state_machine.py."""

from __future__ import annotations

from .state_machine import FORWARD_MOVES

# Deferred moves reuse the same table as forward moves.
# Any (stage, action) → target_stage rule applies in both contexts:
# immediately after agent output AND during deferred move recovery.
DEFERRED_MOVE_RULES = FORWARD_MOVES


def resolve_deferred_target(stage: str, action: str) -> str | None:
    """Return the target stage for a deferred move, or None if no rule matches."""
    return DEFERRED_MOVE_RULES.get((stage, action))
