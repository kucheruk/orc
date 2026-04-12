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
from orc_core.board.kanban_pull import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TESTER,
)
from orc_core.agents.kanban_roles import (
    ROLE_TEAMLEAD,
    build_prompt,
    clear_template_cache,
    format_board_summary,
)


class TestBuildPrompt(unittest.TestCase):

    def setUp(self):
        clear_template_cache()
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


if __name__ == "__main__":
    unittest.main()
