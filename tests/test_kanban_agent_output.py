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
from orc_core.agents.kanban_agent_output import process_agent_result


def _setup(tmp: str) -> tuple[Path, KanbanBoard]:
    tasks_dir = init_kanban_board(Path(tmp))
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add(tasks_dir: Path, card: KanbanCard) -> KanbanCard:
    stage_dir = tasks_dir / card.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{card.id}.md"
    card.body = card.body or "body"
    write_card(card, path)
    return card


class TestProductTransition(unittest.TestCase):

    def test_product_sets_architect(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            card = _add(td, KanbanCard(id="P-1", stage="1_Inbox", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = board.card_by_id("P-1")

            # Simulate agent updating the file
            card_on_disk = card
            card_on_disk.action = "Architect"
            card_on_disk.value_score = 80
            write_card(card_on_disk)

            original = KanbanCard(
                id="P-1", stage="1_Inbox", action="Product",
                file_path=card.file_path,
            )
            errors = process_agent_result(board, original, "product")
            self.assertEqual(errors, [])
            # Card should have moved to 2_Estimate
            updated = board.card_by_id("P-1")
            self.assertEqual(updated.stage, "2_Estimate")

    def test_invalid_product_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            card = _add(td, KanbanCard(id="P-2", stage="1_Inbox", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = board.card_by_id("P-2")

            # Simulate agent setting invalid action
            card.action = "Done"
            write_card(card)

            original = KanbanCard(
                id="P-2", stage="1_Inbox", action="Product",
                file_path=card.file_path,
            )
            errors = process_agent_result(board, original, "product")
            self.assertTrue(len(errors) > 0)


class TestCoderTransition(unittest.TestCase):

    def test_coder_sends_to_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            card = _add(td, KanbanCard(id="C-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = board.card_by_id("C-1")

            card.action = "Reviewing"
            write_card(card)

            original = KanbanCard(
                id="C-1", stage="4_Coding", action="Coding",
                file_path=card.file_path,
            )
            errors = process_agent_result(board, original, "coder")
            self.assertEqual(errors, [])
            updated = board.card_by_id("C-1")
            self.assertEqual(updated.stage, "5_Review")


class TestReviewerLoopCount(unittest.TestCase):

    def test_reviewer_sends_back_increments_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            card = _add(td, KanbanCard(
                id="R-1", stage="5_Review", action="Reviewing", loop_count=0,
            ))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = board.card_by_id("R-1")

            card.action = "Coding"
            write_card(card)

            original = KanbanCard(
                id="R-1", stage="5_Review", action="Reviewing",
                loop_count=0, file_path=card.file_path,
            )
            errors = process_agent_result(board, original, "reviewer")
            self.assertEqual(errors, [])
            updated = board.card_by_id("R-1")
            self.assertEqual(updated.loop_count, 1)
            # Card stays in 5_Review (no left movement)
            self.assertEqual(updated.stage, "5_Review")


class TestProtectedFields(unittest.TestCase):

    def test_agent_cannot_change_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            card = _add(td, KanbanCard(id="X-1", stage="4_Coding", action="Coding"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = board.card_by_id("X-1")

            card.action = "Reviewing"
            card.id = "HACKED"
            write_card(card)

            original = KanbanCard(
                id="X-1", stage="4_Coding", action="Coding",
                file_path=card.file_path,
            )
            errors = process_agent_result(board, original, "coder")
            self.assertTrue(any("id" in e for e in errors))


class TestCardValidation(unittest.TestCase):

    def test_valid_card_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            card = _add(td, KanbanCard(
                id="V-4", stage="1_Inbox", action="Product",
                value_score=50, effort_score=30,
            ))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = board.card_by_id("V-4")

            card.action = "Architect"
            card.value_score = 80
            write_card(card)

            original = KanbanCard(
                id="V-4", stage="1_Inbox", action="Product",
                file_path=card.file_path,
            )
            errors = process_agent_result(board, original, "product")
            self.assertEqual(errors, [])


class TestKanbanTaskSource(unittest.TestCase):

    def test_list_tasks(self):
        from orc_core.board.kanban_task_source import KanbanTaskSource
        with tempfile.TemporaryDirectory() as tmp:
            td = init_kanban_board(Path(tmp))
            _add(td, KanbanCard(id="TS-1", stage="4_Coding", action="Coding", title="Code it"))
            _add(td, KanbanCard(id="TS-2", stage="8_Done", action="Done", title="Done task"))
            source = KanbanTaskSource(td)
            tasks = source.list_tasks()
            self.assertEqual(len(tasks), 2)
            open_tasks = source.get_open_tasks()
            self.assertEqual(len(open_tasks), 1)
            self.assertEqual(open_tasks[0].task_id, "TS-1")

    def test_is_task_done(self):
        from orc_core.board.kanban_task_source import KanbanTaskSource
        with tempfile.TemporaryDirectory() as tmp:
            td = init_kanban_board(Path(tmp))
            _add(td, KanbanCard(id="TS-3", stage="8_Done", action="Done", title="Finished"))
            source = KanbanTaskSource(td)
            self.assertTrue(source.is_task_done("TS-3"))
            self.assertFalse(source.is_task_done("nonexistent"))


if __name__ == "__main__":
    unittest.main()
