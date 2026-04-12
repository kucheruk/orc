#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.infra.adapters.fs_card_repository import FsCardRepository

write_card = FsCardRepository().write_card
from orc_core.board.kanban_init import init_kanban_board


def _make_board(tmp: str) -> tuple[Path, KanbanBoard]:
    root = Path(tmp)
    tasks_dir = init_kanban_board(root)
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add_card(tasks_dir: Path, card: KanbanCard) -> None:
    stage_dir = tasks_dir / card.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{card.id}.md"
    card.body = card.body or "test body"
    write_card(card, path)


class TestBoardRefresh(unittest.TestCase):

    def test_empty_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _make_board(tmp)
            self.assertEqual(len(board.cards), 0)

    def test_reads_cards_from_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="T-1", stage="1_Inbox", action="Product"))
            _add_card(tasks_dir, KanbanCard(id="T-2", stage="4_Coding", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            self.assertEqual(len(board.cards), 2)
            self.assertEqual(board.stage_count("1_Inbox"), 1)
            self.assertEqual(board.stage_count("4_Coding"), 1)

    def test_trusts_folder_over_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            # Card says stage=3_Todo but lives in 4_Coding folder
            card = KanbanCard(id="T-X", stage="3_Todo", action="Coding")
            stage_dir = tasks_dir / "4_Coding"
            write_card(card, stage_dir / "T-X.md")
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            loaded = board.card_by_id("T-X")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.stage, "4_Coding")


class TestWIPLimits(unittest.TestCase):

    def test_default_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _make_board(tmp)
            self.assertEqual(board.wip_limit("4_Coding"), 3)
            self.assertEqual(board.wip_limit("7_Handoff"), 2)

    def test_custom_limit_from_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            idx = tasks_dir / "4_Coding" / "_index.md"
            idx.write_text("---\nstage: 4_Coding\nwip_limit: 1\n---\n")
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            self.assertEqual(board.wip_limit("4_Coding"), 1)

    def test_has_wip_room(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            idx = tasks_dir / "4_Coding" / "_index.md"
            idx.write_text("---\nstage: 4_Coding\nwip_limit: 1\n---\n")
            _add_card(tasks_dir, KanbanCard(id="C-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            self.assertFalse(board.has_wip_room("4_Coding"))

    def test_inbox_has_no_wip_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _make_board(tmp)
            self.assertTrue(board.has_wip_room("1_Inbox"))
            self.assertTrue(board.has_wip_room("8_Done"))


class TestPickBest(unittest.TestCase):

    def test_expedite_beats_standard(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(
                id="S-1", stage="4_Coding", action="Coding",
                class_of_service="standard", value_score=90, effort_score=10,
            ))
            _add_card(tasks_dir, KanbanCard(
                id="E-1", stage="4_Coding", action="Coding",
                class_of_service="expedite", cos_justification="fire",
                value_score=10, effort_score=90,
            ))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            best = board.pick_best("4_Coding", "Coding")
            self.assertEqual(best.id, "E-1")

    def test_standard_sorted_by_roi(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(
                id="L-1", stage="3_Todo", action="Coding",
                value_score=20, effort_score=80,
            ))
            _add_card(tasks_dir, KanbanCard(
                id="H-1", stage="3_Todo", action="Coding",
                value_score=80, effort_score=20,
            ))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            best = board.pick_best("3_Todo", "Coding")
            self.assertEqual(best.id, "H-1")

    def test_skip_assigned_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(
                id="A-1", stage="4_Coding", action="Coding", assigned_agent="s2",
            ))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            best = board.pick_best("4_Coding", "Coding")
            self.assertIsNone(best)

    def test_skip_unmet_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(
                id="D-1", stage="3_Todo", action="Coding",
                dependencies=["D-0"],
            ))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            best = board.pick_best("3_Todo", "Coding")
            self.assertIsNone(best)


class TestMoveCard(unittest.TestCase):

    def test_move_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="M-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            card = board.card_by_id("M-1")
            board.move_card(card, "5_Review")
            self.assertEqual(card.stage, "5_Review")
            self.assertTrue(card.file_path.exists())
            self.assertFalse((tasks_dir / "4_Coding" / "M-1.md").exists())

    def test_move_left_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="M-2", stage="5_Review", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            card = board.card_by_id("M-2")
            with self.assertRaises(ValueError):
                board.move_card(card, "4_Coding")

    def test_move_respects_wip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            idx = tasks_dir / "5_Review" / "_index.md"
            idx.write_text("---\nstage: 5_Review\nwip_limit: 1\n---\n")
            _add_card(tasks_dir, KanbanCard(id="W-1", stage="5_Review", action="Reviewing"))
            _add_card(tasks_dir, KanbanCard(id="W-2", stage="4_Coding", action="Reviewing"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            card = board.card_by_id("W-2")
            with self.assertRaises(ValueError):
                board.move_card(card, "5_Review")


class TestBoardSummary(unittest.TestCase):

    def test_summary_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="S-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            summary = board.summary()
            self.assertIn("4_Coding", summary)
            self.assertEqual(summary["4_Coding"]["count"], 1)
            self.assertEqual(summary["4_Coding"]["wip_limit"], 3)


class TestCardLock(unittest.TestCase):

    def test_same_card_id_returns_same_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _make_board(tmp)
            lock1 = board.card_lock("TASK-001")
            lock2 = board.card_lock("TASK-001")
            self.assertIs(lock1, lock2)

    def test_different_cards_get_different_locks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _make_board(tmp)
            lock_a = board.card_lock("A")
            lock_b = board.card_lock("B")
            self.assertIsNot(lock_a, lock_b)

    def test_card_lock_provides_mutual_exclusion(self):
        import threading
        import time

        with tempfile.TemporaryDirectory() as tmp:
            _, board = _make_board(tmp)
            counter = [0]
            max_concurrent = [0]
            barrier = threading.Barrier(2)

            def worker():
                barrier.wait()
                lock = board.card_lock("X")
                with lock:
                    counter[0] += 1
                    current = counter[0]
                    if current > max_concurrent[0]:
                        max_concurrent[0] = current
                    time.sleep(0.02)
                    counter[0] -= 1

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start(); t2.start()
            t1.join(); t2.join()
            self.assertEqual(max_concurrent[0], 1)


class TestCallbackWarnings(unittest.TestCase):

    def test_move_callback_error_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="CB-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            board.on_move(lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))

            card = board.card_by_id("CB-1")
            board.move_card(card, "5_Review")
            # Card moved despite callback error
            self.assertEqual(card.stage, "5_Review")

    def test_action_change_callback_error_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, _ = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="CB-2", stage="4_Coding", action="Coding"))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            board.on_action_change(lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))

            card = board.card_by_id("CB-2")
            card.action = "Reviewing"
            board.save_card(card, old_action="Coding", role="coder")
            # Card saved despite callback error
            self.assertEqual(card.action, "Reviewing")


class TestInitBoard(unittest.TestCase):

    def test_creates_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir = init_kanban_board(Path(tmp))
            self.assertTrue(tasks_dir.is_dir())
            for stage in ("1_Inbox", "2_Estimate", "3_Todo", "4_Coding",
                          "5_Review", "6_Testing", "7_Handoff", "8_Done"):
                self.assertTrue((tasks_dir / stage).is_dir())
            # WIP index files exist
            self.assertTrue((tasks_dir / "4_Coding" / "_index.md").exists())
            # No index for Inbox
            self.assertFalse((tasks_dir / "1_Inbox" / "_index.md").exists())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            init_kanban_board(Path(tmp))
            init_kanban_board(Path(tmp))  # should not raise


if __name__ == "__main__":
    unittest.main()
