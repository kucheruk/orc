#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard, parse_card
from orc_core.board.kanban_init import init_kanban_board
from orc_core.board.use_cases.create_card import create_inbox_card


class CardStateVersionTest(unittest.TestCase):
    def test_parse_missing_state_version_defaults_to_zero(self):
        card = parse_card("---\nid: TASK-1\n---\nbody")
        self.assertEqual(card.state_version, 0)

    def test_create_save_move_assign_release_bump_state_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir = init_kanban_board(Path(tmp))
            board = KanbanBoard(tasks_dir, repo=FsCardRepository())

            card = create_inbox_card(board, "Structured results", card_id="TASK-100")
            self.assertEqual(card.state_version, 1)

            card.title = "Structured results v2"
            board.save_card(card)
            self.assertEqual(card.state_version, 2)

            board.assign_agent(card, "s1")
            self.assertEqual(card.state_version, 3)

            board.release_agent(card)
            self.assertEqual(card.state_version, 4)

            board.move_card(card, "2_Estimate")
            self.assertEqual(card.state_version, 5)

            loaded = board.repo.read_card(card.file_path)
            self.assertEqual(loaded.state_version, 5)


if __name__ == "__main__":
    unittest.main()
