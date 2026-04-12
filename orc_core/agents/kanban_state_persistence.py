#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban state persistence: save/load card_fail_counts and worktree cleanup."""

from __future__ import annotations

import logging
from pathlib import Path

from ..infra.io.atomic_io import write_json_atomic
from ..infra.io.logging import log_event
from ..infra.state.state_paths import kanban_state_path

_logger = logging.getLogger(__name__)


def load_kanban_state(workdir: str) -> tuple[dict[str, int], dict[str, int]]:
    """Load persisted card_fail_counts and arbitrated_at_loop from disk."""
    path = kanban_state_path(workdir)
    if not path.exists():
        return {}, {}
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        fail_counts = {k: int(v) for k, v in data.get("card_fail_counts", {}).items()}
        arb_loop = {k: int(v) for k, v in data.get("arbitrated_at_loop", {}).items()}
        return fail_counts, arb_loop
    except Exception as exc:
        _logger.warning("Failed to load kanban state: %s", exc)
        return {}, {}


def save_kanban_state(
    workdir: str,
    card_fail_counts: dict[str, int],
    arbitrated_at_loop: dict[str, int],
) -> None:
    """Persist card_fail_counts and arbitrated_at_loop to disk."""
    path = kanban_state_path(workdir)
    write_json_atomic(path, {
        "card_fail_counts": card_fail_counts,
        "arbitrated_at_loop": arbitrated_at_loop,
    })


def release_stale_agents(board, publisher) -> set[str]:
    """Release cards stuck with assigned_agent from a crashed previous run.

    Returns set of done card IDs (for worktree cleanup).
    """
    released = 0
    done_ids: set[str] = set()
    for card in list(board.cards):
        if card.is_done:
            done_ids.add(card.id)
        if card.is_assigned and not card.is_done:
            old_agent = card.assigned_agent
            board.release_agent(card)
            released += 1
            publisher._emit("system", card.id, f"{card.id} released stale agent {old_agent}")
    if released:
        publisher._emit("system", "", f"Released {released} stale agent(s) from previous run")
    return done_ids


def cleanup_done_worktrees(
    done_ids: set[str], workdir: str, log_path: Path, publisher,
) -> None:
    """Remove worktrees for cards that reached Done."""
    from ..git.worktree_flow import WorktreeSession, _safe_name, cleanup_task_worktree
    from ..infra.state.state_paths import worktrees_root

    wt_root = worktrees_root(workdir)
    if not wt_root.exists():
        return
    cleaned = 0
    for card_id in done_ids:
        safe = _safe_name(card_id)
        wt_path = wt_root / safe
        if wt_path.exists():
            session = WorktreeSession(
                base_workdir=workdir,
                worktree_path=str(wt_path),
                branch_name=f"orc/{safe}",
                task_id=card_id,
            )
            try:
                cleanup_task_worktree(session, log_path)
                cleaned += 1
            except Exception as exc:
                log_event(log_path, "WARN", "failed to cleanup done worktree",
                          task_id=card_id, error=str(exc)[:200])
    if cleaned:
        publisher._emit("system", "", f"Cleaned {cleaned} worktree(s) from completed cards")
