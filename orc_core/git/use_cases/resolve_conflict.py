#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: resolve a cherry-pick conflict."""

from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING

from ..conflict_resolver import ConflictResolver

if TYPE_CHECKING:
    from ..integration_manager import IntegrationContext


def resolve_conflict(
    resolver: ConflictResolver,
    ctx: "IntegrationContext",
    initial_attempt,
    merge_expert_fn: Optional[Callable[[], bool]],
    abort_fn: Callable[["IntegrationContext"], None],
) -> bool:
    """Run conflict-resolution flow on a cherry-pick conflict.

    Thin wrapper over ``ConflictResolver.resolve`` — tries auto-resolve first
    then falls back to the merge expert.
    """
    return resolver.resolve(ctx, initial_attempt, merge_expert_fn, abort_fn)
