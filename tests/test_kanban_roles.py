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
)
from orc_core.agents.roles import (
    ROLE_TEAMLEAD,
    build_prompt,
    build_teamlead_prompt,
    format_board_detail,
    format_board_summary,
)


class TestBuildPrompt(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.tasks_dir = init_kanban_board(Path(self.tmp))
        card = KanbanCard(id="T-1", title="Test task", stage="4_Coding", action="Coding", body="body")
        stage_dir = self.tasks_dir / "4_Coding"
        write_card(card, stage_dir / "T-1.md")
        self.board = KanbanBoard(self.tasks_dir, repo=FsCardRepository())
        self.card = self.board.card_by_id("T-1")

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_roles_produce_nonempty_prompt(self):
        roles = [ROLE_PRODUCT, ROLE_ARCHITECT, ROLE_CODER, ROLE_REVIEWER,
                 ROLE_TESTER, ROLE_INTEGRATOR, ROLE_TEAMLEAD]
        for role in roles:
            with self.subTest(role=role):
                prompt = build_prompt(role, self.card, self.board)
                self.assertIsInstance(prompt, str)
                self.assertGreater(len(prompt), 100)

    def test_prompt_contains_card_id(self):
        prompt = build_prompt(ROLE_CODER, self.card, self.board)
        self.assertIn("T-1", prompt)

    def test_prompt_contains_board_summary(self):
        prompt = build_prompt(ROLE_CODER, self.card, self.board)
        self.assertIn("4_Coding", prompt)
        self.assertIn("Stage", prompt)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            build_prompt("unknown_role", self.card, self.board)


class TestBoardSummary(unittest.TestCase):

    def test_format_has_all_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir = init_kanban_board(Path(tmp))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())
            summary = format_board_summary(board)
            self.assertIn("1_Inbox", summary)
            self.assertIn("8_Done", summary)
            self.assertIn("Stage", summary)


class TestHealthModeCompactBoard(unittest.TestCase):

    def _make_board(self, tmp: Path) -> KanbanBoard:
        tasks_dir = init_kanban_board(tmp)
        for cid, title in (
            ("HC-1", "One card in estimate"),
            ("HC-2", "Another in estimate with deps"),
        ):
            card = KanbanCard(
                id=cid, title=title, stage="2_Estimate", action="Product",
                body="body", dependencies=["HC-1"] if cid == "HC-2" else [],
            )
            write_card(card, tasks_dir / "2_Estimate" / f"{cid}.md")
        return KanbanBoard(tasks_dir, repo=FsCardRepository())

    def test_compact_board_drops_title_and_keeps_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = self._make_board(Path(tmp))
            rendered = format_board_detail(board, compact=True)
            self.assertIn("HC-1", rendered)
            self.assertIn("action=Product", rendered)
            self.assertIn("loop=0", rendered)
            self.assertIn("deps=1(1 unmet)", rendered)  # HC-2 has one unmet dep
            self.assertNotIn("One card in estimate", rendered)  # title stripped
            self.assertNotIn("| Title |", rendered)            # no table header

    def test_health_prompt_uses_compact_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = self._make_board(Path(tmp))
            prompt = build_teamlead_prompt(
                mode="health", board=board,
                diagnostic_info="test alert",
                decision_path=str(Path(tmp) / ".orc" / "decision.md"),
            )
            self.assertIn("action=Product", prompt)
            self.assertNotIn("| Title |", prompt)

    def test_arbitration_prompt_still_uses_full_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            board = self._make_board(Path(tmp))
            card = board.card_by_id("HC-1")
            prompt = build_teamlead_prompt(
                mode="arbitration", board=board, card=card,
                decision_path=str(Path(tmp) / ".orc" / "decision.md"),
            )
            self.assertIn("| Title |", prompt)


if __name__ == "__main__":
    unittest.main()
