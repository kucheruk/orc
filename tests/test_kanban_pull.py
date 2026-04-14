#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.fs_card_repository import FsCardRepository

write_card = FsCardRepository().write_card
from orc_core.board.kanban_init import init_kanban_board
from orc_core.board.kanban_pull import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TESTER,
    find_next_work,
    find_teamlead_work,
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


class TestPullPriority(unittest.TestCase):
    """Pull system should prefer rightmost columns."""

    def test_handoff_before_coding(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="H-1", stage="7_Handoff", action="Integrating"))
            _add(td, KanbanCard(id="C-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertIsNotNone(result)
            self.assertEqual(result.card.id, "H-1")
            self.assertEqual(result.role, ROLE_INTEGRATOR)

    def test_testing_before_coding(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="T-1", stage="6_Testing", action="Testing"))
            _add(td, KanbanCard(id="C-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertEqual(result.card.id, "T-1")
            self.assertEqual(result.role, ROLE_TESTER)

    def test_review_before_new_coding(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="R-1", stage="5_Review", action="Reviewing"))
            _add(td, KanbanCard(id="C-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertEqual(result.card.id, "R-1")
            self.assertEqual(result.role, ROLE_REVIEWER)

    def test_coding_fix_in_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="F-1", stage="5_Review", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertEqual(result.card.id, "F-1")
            self.assertEqual(result.role, ROLE_CODER)
            self.assertTrue(result.needs_worktree)

    def test_coding_fix_in_testing(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="F-1", stage="6_Testing", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertEqual(result.card.id, "F-1")
            self.assertEqual(result.role, ROLE_CODER)

    def test_estimate_architect(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="E-1", stage="2_Estimate", action="Architect"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertEqual(result.card.id, "E-1")
            self.assertEqual(result.role, ROLE_ARCHITECT)

    def test_inbox_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="I-1", stage="1_Inbox", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertEqual(result.card.id, "I-1")
            self.assertEqual(result.role, ROLE_PRODUCT)

    def test_empty_board_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, board = _setup(tmp)
            result = find_next_work(board)
            self.assertIsNone(result)


class TestTodoPull(unittest.TestCase):

    def test_pulls_from_todo_to_coding(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="P-1", stage="3_Todo", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertIsNotNone(result)
            self.assertEqual(result.card.id, "P-1")
            self.assertEqual(result.role, ROLE_CODER)
            # Card should have been moved to 4_Coding
            self.assertEqual(result.card.stage, "4_Coding")

    def test_no_pull_when_coding_wip_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            idx = td / "4_Coding" / "_index.md"
            idx.write_text("---\nstage: 4_Coding\nwip_limit: 1\n---\n")
            _add(td, KanbanCard(id="C-1", stage="4_Coding", action="Coding"))
            _add(td, KanbanCard(id="T-1", stage="3_Todo", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            # Should pick C-1 (existing coding), not pull T-1
            self.assertEqual(result.card.id, "C-1")


class TestWIPGating(unittest.TestCase):

    def test_reviewer_blocked_when_testing_full(self):
        """Reviewer can't approve if Testing column is at WIP limit."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            idx = td / "6_Testing" / "_index.md"
            idx.write_text("---\nstage: 6_Testing\nwip_limit: 1\n---\n")
            _add(td, KanbanCard(id="T-1", stage="6_Testing", action="Testing"))
            _add(td, KanbanCard(id="R-1", stage="5_Review", action="Reviewing"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            # Testing card should be picked (rightmost), not review
            self.assertEqual(result.card.id, "T-1")


class TestTeamlead(unittest.TestCase):

    def test_finds_looping_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="L-1", stage="5_Review", action="Coding", loop_count=3))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board, loop_threshold=2)
            self.assertIsNotNone(card)
            self.assertEqual(card.id, "L-1")

    def test_finds_blocked_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="B-1", stage="5_Review", action="Blocked"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board)
            self.assertIsNotNone(card)
            self.assertEqual(card.id, "B-1")

    def test_no_teamlead_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="OK-1", stage="4_Coding", action="Coding", loop_count=0))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board)
            self.assertIsNone(card)


class TestWorktreeFlag(unittest.TestCase):

    def test_coder_needs_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="W-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertTrue(result.needs_worktree)

    def test_integrator_uses_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="W-2", stage="7_Handoff", action="Integrating"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertTrue(result.needs_worktree)

    def test_product_no_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="W-3", stage="1_Inbox", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertFalse(result.needs_worktree)


if __name__ == "__main__":
    unittest.main()
