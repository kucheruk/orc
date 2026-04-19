#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic auto-unblock helpers for teamlead flow recovery."""

from __future__ import annotations

from datetime import datetime, timezone

from ...board.card_sections import SECTION_DESIGN, SECTION_FEEDBACK, SECTION_NOTES, SECTION_PRODUCT
from ...board.stage_constants import STAGE_DONE
from ...board.use_cases.create_card import create_inbox_card
from ...log import log_event

_CYCLE_CARD_PREFIX = "[AUTO-UNBLOCK] Resolve cycle"


def resolve_cycle_with_decomposition(ctx, diagnostic) -> bool:
    """Break a dependency cycle by introducing a decomposition card and rewiring one edge."""
    if not getattr(diagnostic, "cycle_edges", ()):
        return False
    edge = diagnostic.cycle_edges[0]
    from_id, to_id = edge
    source = ctx.distributor.board.card_by_id(from_id)
    target = ctx.distributor.board.card_by_id(to_id)
    if source is None or target is None:
        return False
    title = f"{_CYCLE_CARD_PREFIX} {from_id}->{to_id}"
    decomposition = _find_existing_cycle_card(ctx.distributor.board.cards, title)
    if decomposition is None:
        decomposition = create_inbox_card(ctx.distributor.board, title)
        decomposition.body = (
            f"{SECTION_PRODUCT}\n\n"
            f"Break dependency cycle `{from_id} -> {to_id}` with explicit decomposition.\n"
            "- Define independent increments for both cards.\n"
            "- Agree minimal interface/event contract between them.\n"
            "- Remove cyclic coupling and update dependencies.\n\n"
            f"{SECTION_DESIGN}\n\n(Architect fills)\n\n"
            f"{SECTION_NOTES}\n\n(Coder fills)\n\n"
            f"{SECTION_FEEDBACK}\n\n(Reviewer/Tester fills)\n"
        )
        ctx.distributor.board.save_card(decomposition)
    changed = False
    if to_id in source.dependencies:
        source.dependencies = [d for d in source.dependencies if d != to_id]
        changed = True
    if decomposition.id not in source.dependencies:
        source.dependencies.append(decomposition.id)
        changed = True
    if changed:
        ctx.distributor.board.save_card(source)
    feedback = (
        "## TEAMLEAD AUTO-UNBLOCK\n"
        f"Cycle detected and rewired: removed `{to_id}` dependency from `{from_id}`.\n"
        f"Added decomposition dependency `{decomposition.id}` ({title})."
    )
    _append_feedback(source, feedback)
    _append_feedback(target, feedback)
    ctx.publisher.emit(
        "teamlead",
        source.id,
        f"Auto-unblock cycle {from_id}->{to_id}; decomposition card {decomposition.id}",
    )
    ctx.notifier.notify_cycle_autounblock(from_id, to_id, decomposition.id)
    log_event(
        ctx.log_path,
        "WARN",
        "teamlead auto-unblock cycle resolved",
        from_card=from_id,
        to_card=to_id,
        decomposition_card=decomposition.id,
    )
    return True


def release_stale_assignments(ctx, suspect_counts: dict[str, int], *, stale_minutes: int = 20, suspect_threshold: int = 2) -> int:
    """Release cards assigned to stale/missing agent sessions."""
    active_by_session = ctx.active_tasks_provider()
    released = 0
    for card in ctx.distributor.board.cards:
        if card.stage == STAGE_DONE or not card.assigned_agent:
            suspect_counts.pop(card.id, None)
            continue
        assigned = card.assigned_agent
        active_task = active_by_session.get(assigned, "")
        stale = _minutes_since(card.updated_at) >= stale_minutes
        same_task_running = active_task == card.id
        if not stale or same_task_running:
            suspect_counts.pop(card.id, None)
            continue
        suspect_counts[card.id] = suspect_counts.get(card.id, 0) + 1
        if suspect_counts[card.id] < suspect_threshold:
            continue
        suspect_counts.pop(card.id, None)
        ctx.distributor.board.release_agent(card)
        note = (
            "## TEAMLEAD AUTO-UNBLOCK\n"
            f"Released stale assignment `{assigned}` after {stale_minutes}+ minutes without matching runtime task.\n"
            f"Runtime session task: `{active_task or 'none'}`."
        )
        _append_feedback(card, note)
        ctx.publisher.emit(
            "teamlead",
            card.id,
            f"Released stale assignment for {card.id} from {assigned} (active={active_task or 'none'})",
        )
        log_event(
            ctx.log_path,
            "WARN",
            "teamlead auto-unblock stale assignment released",
            card_id=card.id,
            assigned_agent=assigned,
            runtime_task=active_task,
        )
        released += 1
    if released:
        ctx.notifier.notify_stale_assignments_released(released)
    return released


def _find_existing_cycle_card(cards, title: str):
    for card in cards:
        if card.title == title and card.stage != STAGE_DONE:
            return card
    return None


def _append_feedback(card, text: str) -> None:
    body = card.body or ""
    if SECTION_FEEDBACK in body:
        card.body = body.rstrip() + f"\n\n{text}\n"
    else:
        card.body = body.rstrip() + f"\n\n{SECTION_FEEDBACK}\n\n{text}\n"


def _minutes_since(iso_ts: str) -> float:
    if not iso_ts:
        return 10**9
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds() / 60.0
    except Exception:
        return 10**9
