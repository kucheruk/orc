#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.kanban_init import init_kanban_board
from orc_core.tasks.use_cases.mark_task_blocked import mark_task_blocked
from orc_core.tasks.use_cases.process_task_result import escalate_if_threshold_reached


def _setup_board(tmp: str) -> tuple[Path, KanbanBoard]:
    tasks_dir = init_kanban_board(Path(tmp))
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add_card(tasks_dir: Path, board: KanbanBoard, card: KanbanCard) -> KanbanCard:
    stage_dir = tasks_dir / card.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{card.id}.md"
    card.body = card.body or "body"
    FsCardRepository().write_card(card, path)
    board.refresh(force=True)
    return card


class BlockedCardEscalationTest(unittest.TestCase):
    def test_mark_task_blocked_moves_terminal_card_back_to_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            _add_card(tasks_dir, board, KanbanCard(id="JOB-001", stage="8_Done", action="Done"))
            card = board.card_by_id("JOB-001")

            mark_task_blocked(card, board, reason="human attention")

            updated = board.card_by_id("JOB-001")
            self.assertEqual(updated.stage, "7_Handoff")
            self.assertEqual(updated.action, "Blocked")

    def test_repeated_failures_block_and_move_card_to_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _setup_board(tmp)
            _add_card(tasks_dir, board, KanbanCard(id="AUTH-003", stage="6_Testing", action="Testing"))
            card = board.card_by_id("AUTH-003")
            outcomes = MagicMock()
            outcomes.increment_fail_count.return_value = 3
            publisher = MagicMock()
            notifier = MagicMock()

            blocked = escalate_if_threshold_reached(
                card,
                "max_restarts_exceeded",
                board,
                outcomes,
                publisher,
                notifier,
                Path(tmp) / "orc.log",
            )

            self.assertTrue(blocked)
            updated = board.card_by_id("AUTH-003")
            self.assertEqual(updated.stage, "7_Handoff")
            self.assertEqual(updated.action, "Blocked")


if __name__ == "__main__":
    unittest.main()
