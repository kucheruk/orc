#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Board health analysis: deadlock detection, circular deps, stuck cards.

Extracted from KanbanBoard to follow SRP — the board manages state,
this module analyzes health.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .kanban_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_TODO,
)

if TYPE_CHECKING:
    from .kanban_card import KanbanCard


def detect_wip_deadlock(
    cards: list[KanbanCard],
    wip_limits: dict[str, int],
) -> str:
    """Detect WIP deadlock conditions. Returns diagnostic string or '' if healthy.

    A WIP deadlock occurs when work exists but no agent can pick it because:
    - A WIP-limited stage is full AND all its cards have unmet dependencies
    - The stages feeding those dependencies cannot be processed due to WIP constraints
    """
    non_done = [c for c in cards if c.stage != STAGE_DONE]
    if not non_done:
        return ""
    # Check if ANY card is assignable (not assigned, correct action, deps met)
    assignable = [c for c in non_done if not c.assigned_agent]
    if not assignable:
        return ""  # cards exist but all assigned — not a deadlock, just busy

    done_ids = {c.id for c in cards if c.stage == STAGE_DONE}
    todo = [c for c in cards if c.stage == STAGE_TODO]
    todo_limit = wip_limits.get(STAGE_TODO, 999)
    todo_full = len(todo) >= todo_limit and todo_limit < 999

    if todo_full and todo:
        todo_all_blocked = all(
            any(dep not in done_ids for dep in c.dependencies)
            for c in todo if c.dependencies
        )
        todo_no_deps = [c for c in todo if not c.dependencies and not c.assigned_agent]
        if todo_all_blocked and not todo_no_deps:
            estimate = [c for c in cards if c.stage == STAGE_ESTIMATE]
            needed_deps: set[str] = set()
            for c in todo:
                for dep in c.dependencies:
                    if dep not in done_ids:
                        needed_deps.add(dep)
            blocking_estimate = [c for c in estimate if c.id in needed_deps]
            if blocking_estimate:
                blocked_ids = ", ".join(c.id for c in blocking_estimate[:5])
                todo_ids = ", ".join(c.id for c in todo[:5])
                return (
                    f"WIP deadlock: Todo full ({len(todo)}/{todo_limit}) with all deps unmet. "
                    f"Blocked by Estimate cards: [{blocked_ids}]. "
                    f"Todo cards waiting: [{todo_ids}]"
                )

    # Check broader starvation: Coding/Review/Testing all empty, no work can be pulled
    coding = [c for c in cards if c.stage == STAGE_CODING]
    review = [c for c in cards if c.stage == STAGE_REVIEW]
    testing = [c for c in cards if c.stage == STAGE_TESTING]
    handoff = [c for c in cards if c.stage == STAGE_HANDOFF]
    active_work = coding + review + testing + handoff
    if not active_work and todo_full:
        return (
            f"Pipeline starvation: Coding/Review/Testing/Handoff all empty, "
            f"Todo full ({len(todo)}/{todo_limit}) — work cannot flow"
        )

    # Check circular dependencies
    circular = detect_circular_deps(non_done, done_ids)
    if circular:
        return circular

    # Check cards stuck too long
    stuck = detect_stuck_cards(non_done, done_ids)
    if stuck:
        return stuck

    return ""


def detect_circular_deps(cards: list[KanbanCard], done_ids: set[str]) -> str:
    """Detect circular dependency chains among active cards."""
    card_ids = {c.id for c in cards}
    dep_graph: dict[str, list[str]] = {}
    for c in cards:
        active_deps = [d for d in c.dependencies if d in card_ids and d not in done_ids]
        if active_deps:
            dep_graph[c.id] = active_deps

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {cid: WHITE for cid in dep_graph}
    cycle_path: list[str] = []

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for dep in dep_graph.get(node, []):
            if dep not in color:
                continue
            if color[dep] == GRAY:
                cycle_path.append(dep)
                cycle_path.append(node)
                return True
            if color[dep] == WHITE and dfs(dep):
                return True
        color[node] = BLACK
        return False

    for cid in dep_graph:
        if color.get(cid, WHITE) == WHITE:
            if dfs(cid):
                ids = " → ".join(cycle_path[:5])
                return f"Circular dependency detected: {ids}. Cards can never unblock."
    return ""


def detect_stuck_cards(
    cards: list[KanbanCard],
    done_ids: set[str],
    threshold_minutes: int = 45,
) -> str:
    """Detect cards stuck in a non-Done stage for too long."""
    now = datetime.now(timezone.utc)
    stuck: list[str] = []
    for c in cards:
        if c.assigned_agent:
            continue  # currently being worked on
        if not c.updated_at:
            continue
        if c.dependencies and any(dep not in done_ids for dep in c.dependencies):
            continue
        try:
            ts = datetime.fromisoformat(c.updated_at.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            elapsed_min = (now - ts).total_seconds() / 60
            if elapsed_min > threshold_minutes:
                stuck.append(f"{c.id} ({c.stage}, {int(elapsed_min)}m idle)")
        except Exception:
            continue
    if stuck:
        return f"Cards stuck without progress: {', '.join(stuck[:5])}"
    return ""
