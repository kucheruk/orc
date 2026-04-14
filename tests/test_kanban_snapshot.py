#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.fs_card_repository import FsCardRepository

write_card = FsCardRepository().write_card
from orc_core.board.kanban_init import init_kanban_board
from orc_core.board.kanban_snapshot import (
    JournalEntry,
    build_board_snapshot,
)


def _setup(tmp: str) -> tuple[Path, KanbanBoard]:
    tasks_dir = init_kanban_board(Path(tmp))
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add(tasks_dir: Path, card: KanbanCard) -> None:
    stage_dir = tasks_dir / card.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{card.id}.md"
    card.body = card.body or "body"
    write_card(card, path)


class TestBuildBoardSnapshot(unittest.TestCase):

    def test_empty_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            snap = build_board_snapshot(board, {})
            self.assertEqual(len(snap.stages), 8)
            self.assertEqual(snap.metrics.total_cards, 0)
            self.assertEqual(snap.metrics.done_cards, 0)

    def test_counts_cards_per_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="T-1", stage="4_Coding", action="Coding"))
            _add(td, KanbanCard(id="T-2", stage="4_Coding", action="Coding"))
            _add(td, KanbanCard(id="T-3", stage="8_Done", action="Done"))
            board = KanbanBoard(td, repo=FsCardRepository())
            snap = build_board_snapshot(board, {})
            self.assertEqual(snap.metrics.total_cards, 3)
            self.assertEqual(snap.metrics.done_cards, 1)
            coding_stage = [s for s in snap.stages if s.name == "4_Coding"][0]
            self.assertEqual(coding_stage.count, 2)
            self.assertEqual(len(coding_stage.cards), 2)

    def test_blocked_cards_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="B-1", stage="5_Review", action="Blocked"))
            board = KanbanBoard(td, repo=FsCardRepository())
            snap = build_board_snapshot(board, {})
            self.assertEqual(snap.metrics.blocked_cards, 1)

    def test_card_snapshot_has_agent_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="A-1", stage="4_Coding", action="Coding", assigned_agent="s2"))
            board = KanbanBoard(td, repo=FsCardRepository())
            snap = build_board_snapshot(board, {})
            coding = [s for s in snap.stages if s.name == "4_Coding"][0]
            self.assertEqual(coding.cards[0].assigned_agent, "s2")

    def test_lead_time_from_done_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            now = datetime.now(timezone.utc)
            ago = now - timedelta(minutes=10)
            _add(td, KanbanCard(
                id="D-1", stage="8_Done", action="Done",
                created_at=ago.isoformat(timespec="seconds"),
                updated_at=now.isoformat(timespec="seconds"),
            ))
            board = KanbanBoard(td, repo=FsCardRepository())
            snap = build_board_snapshot(board, {})
            self.assertGreater(snap.metrics.avg_lead_time_minutes, 9.0)
            self.assertLess(snap.metrics.avg_lead_time_minutes, 11.0)

    def test_throughput_calculation(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="D-1", stage="8_Done", action="Done"))
            _add(td, KanbanCard(id="D-2", stage="8_Done", action="Done"))
            board = KanbanBoard(td, repo=FsCardRepository())
            started = time.time() - 3600  # 1 hour ago
            snap = build_board_snapshot(board, {}, started_at=started)
            self.assertAlmostEqual(snap.metrics.throughput_per_hour, 2.0, delta=0.2)


class TestJournalEntry(unittest.TestCase):

    def test_format_line(self):
        entry = JournalEntry(
            timestamp=1711712345.0,
            category="move",
            card_id="T-1",
            message="T-1 4_Coding -> 5_Review",
        )
        line = entry.format_line()
        self.assertIn("move", line)
        self.assertIn("T-1", line)

    def test_format_colors(self):
        for cat in ("move", "roi", "complete", "escalate", "inbox"):
            entry = JournalEntry(timestamp=0, category=cat, card_id="X", message="test")
            line = entry.format_line()
            self.assertIn(cat, line)


class TestKanbanPublisher(unittest.TestCase):

    def test_journal_callback_called(self):
        from orc_core.agents.kanban_publisher import KanbanPublisher
        entries: list[JournalEntry] = []
        pub = KanbanPublisher()
        pub.journal_callback = entries.append
        pub.log_inbox("T-1", "New feature")
        pub.log_complete("T-2", "coder", 123.0)
        pub.log_escalate("T-3", "blocked")
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].category, "inbox")
        self.assertEqual(entries[1].category, "complete")
        self.assertEqual(entries[2].category, "escalate")

    def test_no_callback_no_error(self):
        from orc_core.agents.kanban_publisher import KanbanPublisher
        pub = KanbanPublisher()
        pub.log_inbox("T-1", "test")  # should not raise


class TestBoardCreateInbox(unittest.TestCase):

    def test_create_inbox_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            card = board.create_inbox_card("NEW-01", "My feature")
            self.assertEqual(card.id, "NEW-01")
            self.assertEqual(card.stage, "1_Inbox")
            self.assertTrue((td / "1_Inbox" / "NEW-01.md").exists())
            board.refresh()
            self.assertEqual(board.stage_count("1_Inbox"), 1)

    def test_next_card_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="TASK-005", stage="4_Coding", action="Coding"))
            _add(td, KanbanCard(id="TASK-010", stage="1_Inbox", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())
            next_id = board.next_card_id()
            self.assertEqual(next_id, "TASK-011")

    def test_next_card_id_empty_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _setup(tmp)
            next_id = board.next_card_id()
            self.assertEqual(next_id, "TASK-001")


if __name__ == "__main__":
    unittest.main()
