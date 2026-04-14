#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration tests for the kanban pipeline: board → pull → agent output → transitions."""

import tempfile
import unittest
from pathlib import Path

from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.fs_card_repository import FsCardRepository

write_card = FsCardRepository().write_card
from orc_core.board.kanban_init import init_kanban_board
from orc_core.agents.kanban_agent_output import process_agent_result
from orc_core.board.kanban_pull import find_next_work, find_teamlead_work


def _setup(tmp: str) -> tuple[Path, KanbanBoard]:
    tasks_dir = init_kanban_board(Path(tmp))
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add(tasks_dir: Path, board: KanbanBoard, card: KanbanCard) -> KanbanCard:
    stage_dir = tasks_dir / card.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{card.id}.md"
    card.body = card.body or "# 1. Product Requirements\n\n# 2. Technical Design & DoD\n\n# 3. Implementation Notes\n\n# 4. Feedback & Checklist\n"
    write_card(card, path)
    board.refresh(force=True)
    return card


def _simulate_agent(board: KanbanBoard, card: KanbanCard, role: str, **overrides) -> list[str]:
    """Simulate an agent modifying the card file on disk, then run process_agent_result."""
    # Refresh to get fresh card with file_path
    board.refresh(force=True)
    fresh = board.card_by_id(card.id)
    assert fresh is not None, f"Card {card.id} not found on board"

    # Read card from disk, apply overrides, write back (as the agent would)
    disk_card = board.repo.read_card(fresh.file_path)
    for key, value in overrides.items():
        setattr(disk_card, key, value)
    write_card(disk_card)

    # Create original snapshot for process_agent_result
    original = KanbanCard(
        id=fresh.id, stage=fresh.stage, action=fresh.action,
        loop_count=fresh.loop_count, roi=fresh.roi,
        assigned_agent=fresh.assigned_agent, created_at=fresh.created_at,
        file_path=fresh.file_path,
    )
    return process_agent_result(board, original, role)


class TestHappyPath(unittest.TestCase):
    """Card flows from Inbox through all stages to Done."""

    def test_inbox_to_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="HP-1", stage="1_Inbox", action="Product",
                                value_score=80, effort_score=20))

            # Step 1: Product → sets action=Architect
            errors = _simulate_agent(board, board.card_by_id("HP-1"), "product",
                                     action="Architect", value_score=80)
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "2_Estimate")

            # Step 2: Architect → sets action=Product (estimate done, back for prioritization)
            errors = _simulate_agent(board, card, "architect",
                                     action="Product", effort_score=30)
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "2_Estimate")  # stays in Estimate

            # Step 3: Product in Estimate → sets action=Coding (approve for Todo)
            errors = _simulate_agent(board, card, "product", action="Coding")
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "3_Todo")

            # Step 4: Pull moves to Coding, then coder → sets action=Reviewing
            board.move_card(card, "4_Coding", reason="pull: ready")
            errors = _simulate_agent(board, card, "coder", action="Reviewing")
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "5_Review")

            # Step 5: Reviewer → sets action=Testing (approved)
            errors = _simulate_agent(board, card, "reviewer", action="Testing")
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "6_Testing")

            # Step 6: Tester → sets action=Integrating (QA passed)
            errors = _simulate_agent(board, card, "tester", action="Integrating")
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "7_Handoff")

            # Step 7: Integrator → sets action=Done
            errors = _simulate_agent(board, card, "integrator", action="Done")
            self.assertEqual(errors, [])
            card = board.card_by_id("HP-1")
            self.assertEqual(card.stage, "8_Done")
            self.assertEqual(card.action, "Done")


class TestLoopBack(unittest.TestCase):
    """Reviewer rejects, coder fixes, reviewer approves."""

    def test_review_rejection_increments_loop_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="LB-1", stage="5_Review", action="Reviewing",
                                loop_count=0))

            # Reviewer rejects → sends back to Coding
            errors = _simulate_agent(board, board.card_by_id("LB-1"), "reviewer",
                                     action="Coding")
            self.assertEqual(errors, [])
            card = board.card_by_id("LB-1")
            self.assertEqual(card.loop_count, 1)
            self.assertEqual(card.action, "Coding")
            # Card stays in 5_Review (no backward move)
            self.assertEqual(card.stage, "5_Review")

    def test_loop_back_then_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="LB-2", stage="5_Review", action="Reviewing",
                                loop_count=0))

            # Round 1: Reviewer rejects
            _simulate_agent(board, board.card_by_id("LB-2"), "reviewer", action="Coding")
            card = board.card_by_id("LB-2")
            self.assertEqual(card.loop_count, 1)

            # Simulate: coder works on it (card stays in Review with action=Coding)
            # Coder finishes → sets action=Reviewing
            _simulate_agent(board, card, "coder", action="Reviewing")

            # Round 2: Reviewer approves
            errors = _simulate_agent(board, board.card_by_id("LB-2"), "reviewer",
                                     action="Testing")
            self.assertEqual(errors, [])
            card = board.card_by_id("LB-2")
            self.assertEqual(card.stage, "6_Testing")
            self.assertEqual(card.loop_count, 1)  # no increment on approval


class TestAutoDefault(unittest.TestCase):
    """Auto-default behavior when agent doesn't change action."""

    def test_coder_auto_defaults_to_reviewing(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="AD-1", stage="4_Coding", action="Coding"))

            # Coder doesn't change action — system auto-defaults to Reviewing
            errors = _simulate_agent(board, board.card_by_id("AD-1"), "coder")
            self.assertEqual(errors, [])
            card = board.card_by_id("AD-1")
            self.assertEqual(card.stage, "5_Review")
            self.assertEqual(card.action, "Reviewing")

    def test_reviewer_auto_defaults_to_testing(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="AD-2", stage="5_Review", action="Reviewing"))

            errors = _simulate_agent(board, board.card_by_id("AD-2"), "reviewer")
            self.assertEqual(errors, [])
            card = board.card_by_id("AD-2")
            self.assertEqual(card.stage, "6_Testing")

    def test_tester_auto_defaults_to_integrating(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="AD-3", stage="6_Testing", action="Testing"))

            errors = _simulate_agent(board, board.card_by_id("AD-3"), "tester")
            self.assertEqual(errors, [])
            card = board.card_by_id("AD-3")
            self.assertEqual(card.stage, "7_Handoff")

    def test_integrator_auto_defaults_to_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="AD-4", stage="7_Handoff", action="Integrating"))

            errors = _simulate_agent(board, board.card_by_id("AD-4"), "integrator")
            self.assertEqual(errors, [])
            card = board.card_by_id("AD-4")
            self.assertEqual(card.stage, "8_Done")
            self.assertEqual(card.action, "Done")


class TestWIPEnforcement(unittest.TestCase):
    """WIP limits prevent cards from moving into full stages."""

    def test_wip_blocks_movement(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            # Set Review WIP to 1
            board.set_wip_limit("5_Review", 1)
            # Add one card already in Review
            _add(td, board, KanbanCard(id="WP-1", stage="5_Review", action="Reviewing"))
            # Add a card in Coding
            _add(td, board, KanbanCard(id="WP-2", stage="4_Coding", action="Coding"))
            board.refresh(force=True)

            # Coder finishes → action=Reviewing, but Review is full
            errors = _simulate_agent(board, board.card_by_id("WP-2"), "coder",
                                     action="Reviewing")
            self.assertEqual(errors, [])
            card = board.card_by_id("WP-2")
            # Card stays in Coding because Review is at WIP limit
            self.assertEqual(card.stage, "4_Coding")
            self.assertEqual(card.action, "Reviewing")  # action was set

    def test_pull_respects_wip(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            board.set_wip_limit("4_Coding", 1)
            _add(td, board, KanbanCard(id="WP-3", stage="4_Coding", action="Coding"))
            _add(td, board, KanbanCard(id="WP-4", stage="3_Todo", action="Coding"))
            board.refresh(force=True)

            # Pull should not move WP-4 to Coding (WIP full)
            # But it can still pick the card in Coding
            assignment = find_next_work(board)
            self.assertIsNotNone(assignment)
            self.assertEqual(assignment.card.id, "WP-3")  # existing card in Coding


class TestTeamleadDetection(unittest.TestCase):
    """Teamlead picks up looping and blocked cards."""

    def test_picks_up_looping_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="TL-1", stage="5_Review", action="Coding",
                                loop_count=3))
            board.refresh(force=True)

            card = find_teamlead_work(board, loop_threshold=2)
            self.assertIsNotNone(card)
            self.assertEqual(card.id, "TL-1")

    def test_picks_up_blocked_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="TL-2", stage="4_Coding", action="Blocked"))
            board.refresh(force=True)

            card = find_teamlead_work(board)
            self.assertIsNotNone(card)
            self.assertEqual(card.id, "TL-2")

    def test_ignores_assigned_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="TL-3", stage="5_Review", action="Coding",
                                loop_count=3, assigned_agent="s1"))
            board.refresh(force=True)

            card = find_teamlead_work(board, loop_threshold=2)
            self.assertIsNone(card)


class TestValidationRejectsGarbage(unittest.TestCase):
    """Agent output validation catches bad data."""

    def test_invalid_action_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="G-2", stage="4_Coding", action="Coding"))

            errors = _simulate_agent(board, board.card_by_id("G-2"), "coder",
                                     action="Done")
            self.assertTrue(len(errors) > 0)


class TestDependencyBlocking(unittest.TestCase):
    """Cards with unmet dependencies don't move to Todo/Coding."""

    def test_deps_block_promotion_to_todo(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="DEP-1", stage="4_Coding", action="Coding"))
            _add(td, board, KanbanCard(id="DEP-2", stage="2_Estimate", action="Product",
                                dependencies=["DEP-1"]))
            board.refresh(force=True)

            # Product approves DEP-2 for Coding — should be blocked by dependency
            errors = _simulate_agent(board, board.card_by_id("DEP-2"), "product",
                                     action="Coding")
            self.assertEqual(errors, [])
            card = board.card_by_id("DEP-2")
            # Card stays in Estimate because DEP-1 isn't Done
            self.assertEqual(card.stage, "2_Estimate")

    def test_deps_unblock_when_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, board = _setup(tmp)
            _add(td, board, KanbanCard(id="DEP-3", stage="8_Done", action="Done"))
            _add(td, board, KanbanCard(id="DEP-4", stage="2_Estimate", action="Product",
                                dependencies=["DEP-3"]))
            board.refresh(force=True)

            errors = _simulate_agent(board, board.card_by_id("DEP-4"), "product",
                                     action="Coding")
            self.assertEqual(errors, [])
            card = board.card_by_id("DEP-4")
            self.assertEqual(card.stage, "3_Todo")


if __name__ == "__main__":
    unittest.main()
