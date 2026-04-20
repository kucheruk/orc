#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-unblock release semantics for teamlead stale-assignment recovery."""

import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.kanban_init import init_kanban_board
from orc_core.agents.runners.teamlead_autounblock import release_stale_assignments


def _setup_board(tmp: str) -> tuple[Path, KanbanBoard]:
    tasks_dir = init_kanban_board(Path(tmp))
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add_card(
    tasks_dir: Path,
    board: KanbanBoard,
    *,
    card_id: str,
    stage: str,
    action: str,
    assigned: str,
    updated_at: datetime,
) -> KanbanCard:
    card = KanbanCard(
        id=card_id,
        stage=stage,
        action=action,
        assigned_agent=assigned,
        updated_at=updated_at.isoformat(),
    )
    card.body = card.body or "body"
    (tasks_dir / stage).mkdir(parents=True, exist_ok=True)
    FsCardRepository().write_card(card, tasks_dir / stage / f"{card_id}.md")
    board.refresh(force=True)
    return card


def _build_ctx(tmp: str, board: KanbanBoard, active: dict[str, str], known: set[str]):
    """Minimal fake TeamleadContext exposing the 3 providers release_stale_assignments reads."""
    notifier = MagicMock()
    publisher = MagicMock()
    ctx = SimpleNamespace(
        distributor=SimpleNamespace(board=board),
        active_tasks_provider=lambda: active,
        known_sessions_provider=lambda: known,
        notifier=notifier,
        publisher=publisher,
        log_path=Path(tmp) / "orc.log",
    )
    return ctx, notifier, publisher


class ReleaseStaleAssignmentsTest(unittest.TestCase):
    def test_missing_session_releases_immediately_without_stale_buffer(self) -> None:
        """A dangling assigned_agent from a crashed prior ORC must not
        block the pipeline for the full stale-minutes window.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            fresh = datetime.now(timezone.utc) - timedelta(minutes=2)
            _add_card(tasks_dir, board,
                      card_id="NOTIF-002-C-A", stage="4_Coding", action="Coding",
                      assigned="s2", updated_at=fresh)
            # s2 does not exist — new pool has only s1 (teamlead) and s3 (worker)
            ctx, notifier, publisher = _build_ctx(tmp, board, active={"s1": "something"}, known={"s1", "s3"})

            released = release_stale_assignments(ctx, {})

            self.assertEqual(released, 1)
            self.assertEqual(board.card_by_id("NOTIF-002-C-A").assigned_agent, "")
            notifier.notify_stale_assignments_released.assert_called_once_with(1)

    def test_existing_session_busy_elsewhere_still_honours_stale_buffer(self) -> None:
        """If the assigned session exists in the pool but is temporarily
        working on another card, keep the 20-minute buffer + two-cycle
        suspect threshold so a slow agent isn't prematurely unassigned.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            fresh = datetime.now(timezone.utc) - timedelta(minutes=5)  # below 20-min threshold
            _add_card(tasks_dir, board,
                      card_id="X-1", stage="4_Coding", action="Coding",
                      assigned="s2", updated_at=fresh)
            # s2 exists and is running a different card
            ctx, _, _ = _build_ctx(tmp, board, active={"s2": "OTHER"}, known={"s1", "s2"})

            released = release_stale_assignments(ctx, {})

            self.assertEqual(released, 0)
            self.assertEqual(board.card_by_id("X-1").assigned_agent, "s2")

    def test_existing_session_stale_past_buffer_releases_on_second_cycle(self) -> None:
        """Once an assignment crosses the stale_minutes threshold and
        is seen in two consecutive cycles, release it (original
        semantics preserved for the session-exists branch).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            old = datetime.now(timezone.utc) - timedelta(minutes=25)
            _add_card(tasks_dir, board,
                      card_id="X-2", stage="4_Coding", action="Coding",
                      assigned="s2", updated_at=old)
            ctx, _, _ = _build_ctx(tmp, board, active={"s2": "OTHER"}, known={"s1", "s2"})

            suspects: dict[str, int] = {}
            first = release_stale_assignments(ctx, suspects)
            self.assertEqual(first, 0)
            self.assertEqual(suspects.get("X-2"), 1)

            second = release_stale_assignments(ctx, suspects)
            self.assertEqual(second, 1)
            self.assertEqual(board.card_by_id("X-2").assigned_agent, "")

    def test_assigned_session_running_matching_card_is_not_released(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            old = datetime.now(timezone.utc) - timedelta(minutes=90)
            _add_card(tasks_dir, board,
                      card_id="X-3", stage="4_Coding", action="Coding",
                      assigned="s2", updated_at=old)
            # s2 is actively working on X-3 right now
            ctx, _, _ = _build_ctx(tmp, board, active={"s2": "X-3"}, known={"s1", "s2"})

            released = release_stale_assignments(ctx, {})

            self.assertEqual(released, 0)
            self.assertEqual(board.card_by_id("X-3").assigned_agent, "s2")

    def test_done_cards_never_touched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            old = datetime.now(timezone.utc) - timedelta(minutes=120)
            _add_card(tasks_dir, board,
                      card_id="X-4", stage="8_Done", action="Done",
                      assigned="s-gone", updated_at=old)
            ctx, _, _ = _build_ctx(tmp, board, active={}, known={"s1"})

            released = release_stale_assignments(ctx, {})

            self.assertEqual(released, 0)
            self.assertEqual(board.card_by_id("X-4").assigned_agent, "s-gone")


if __name__ == "__main__":
    unittest.main()
