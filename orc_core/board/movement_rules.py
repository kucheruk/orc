#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deferred-move resolver — thin wrapper over FORWARD_MOVES.

Deferred moves (state-recovery path) reuse the same (stage, action) →
target_stage table as forward moves (post-agent-output path).
"""

from __future__ import annotations

from .state_machine import FORWARD_MOVES


def resolve_deferred_target(stage: str, action: str) -> str | None:
    """Return the target stage for a deferred move, or None if no rule matches."""
    return FORWARD_MOVES.get((stage, action))
