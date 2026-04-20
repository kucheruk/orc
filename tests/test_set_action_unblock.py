#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead set_action must route Blocked → anything-else through unblock().

The direct `card.action = action_str` shortcut left loop_count,
finalize_retries, tokens accounting, and the accumulated `## Block
Reason` body sections stale — the card immediately re-blocked on the
next pick_best budget check and ping-ponged Blocked → Arbitration →
Blocked until a human intervened. Route through KanbanCard.unblock()
so those invariants hold.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from orc_core.agents.runners.teamlead_actions.actions.set_action import (
    SetActionHandler,
)
from orc_core.agents.runners.teamlead_actions.registry import ActionContext
from orc_core.board.action_constants import Action
from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.kanban_init import init_kanban_board


def _write(path: Path, card: KanbanCard) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    card.body = card.body or (
        "# 1. Product Requirements\n\n"
        "# 2. Technical Design & DoD\n\n"
        "# 3. Implementation Notes\n\n"
        "# 4. Feedback & Checklist\n"
    )
    FsCardRepository().write_card(card, path)


class TestSetActionUnblocksCleanly(unittest.TestCase):
    def _board(self, tmp: str) -> tuple[Path, KanbanBoard]:
        tasks_dir = init_kanban_board(Path(tmp))
        return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())

    def test_blocked_to_coding_runs_unblock_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = self._board(tmp)
            card = KanbanCard(
                id="X-1", stage="4_Coding", action=Action.BLOCKED,
            )
            card.body = (
                "# 1. Product Requirements\n\nSpec.\n\n"
                "## Block Reason\nagent returned: max_restarts_exceeded\n"
            )
            card.loop_count = 3
            card.finalize_retries = 2
            card.tokens_spent = 321778
            card.tokens_discarded = 0
            card.token_budget = 260000
            _write(tasks_dir / "4_Coding" / "X-1.md", card)
            board.refresh(force=True)

            ctx = ActionContext(
                board=board,
                params={"card_id": "X-1", "action": "Coding"},
                reason="teamlead decided",
                publisher=MagicMock(),
            )
            SetActionHandler().execute(ctx)

            board.refresh(force=True)
            fresh = board.card_by_id("X-1")
            self.assertEqual(fresh.action, Action.CODING)
            self.assertNotIn("Block Reason", fresh.body)
            self.assertEqual(fresh.loop_count, 0)
            self.assertEqual(fresh.finalize_retries, 0)
            self.assertEqual(fresh.tokens_spent, 321778,
                             "tokens_spent preserved for audit")
            self.assertGreaterEqual(fresh.tokens_discarded, 321778,
                                    "tokens_discarded bumped to offset spend")
            self.assertEqual(fresh.tokens_spent_net, 0,
                             "net spend reset so is_budget_exhausted passes")
            self.assertFalse(fresh.is_budget_exhausted)

    def test_blocked_to_blocked_is_noop_for_unblock(self):
        """Re-blocking (Blocked → Blocked) must not trigger unblock cleanup.
        Unlikely path but trivial guard against accidental double-invocation."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = self._board(tmp)
            card = KanbanCard(id="X-2", stage="4_Coding", action=Action.BLOCKED)
            card.body = "# spec\n\n## Block Reason\nstale\n"
            card.loop_count = 5
            _write(tasks_dir / "4_Coding" / "X-2.md", card)
            board.refresh(force=True)

            ctx = ActionContext(
                board=board,
                params={"card_id": "X-2", "action": "Blocked"},
                reason="still blocked",
                publisher=MagicMock(),
            )
            SetActionHandler().execute(ctx)

            board.refresh(force=True)
            fresh = board.card_by_id("X-2")
            # Block Reason and loop_count left intact because no unblock.
            self.assertIn("Block Reason", fresh.body)
            self.assertEqual(fresh.loop_count, 5)

    def test_reject_block_on_card_with_unmet_dependencies(self):
        """Teamlead must not flip a deps-gated card to Blocked. The card
        is already system-gated (pull refuses until deps are Done), and
        Blocked is reserved for human-actionable issues — otherwise
        operators get paged about cards they cannot productively unblock
        (jeeves 2026-04-20: NOTIF-004-B with unmet NOTIF-004-A, and
        QA-003-A with unmet QA-001-C/QA-002-C).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = self._board(tmp)
            upstream = KanbanCard(id="DEP-UP", stage="3_Todo", action=Action.CODING)
            gated = KanbanCard(
                id="DEPS-GATED", stage="2_Estimate", action="Product",
                dependencies=["DEP-UP"],
            )
            _write(tasks_dir / "3_Todo" / "DEP-UP.md", upstream)
            _write(tasks_dir / "2_Estimate" / "DEPS-GATED.md", gated)
            board.refresh(force=True)

            ctx = ActionContext(
                board=board,
                params={"card_id": "DEPS-GATED", "action": "Blocked"},
                reason="teamlead thought it was stuck",
                publisher=MagicMock(),
            )

            with self.assertRaises(ValueError) as raised:
                SetActionHandler().execute(ctx)
            self.assertIn("unmet dependencies", str(raised.exception))

            board.refresh(force=True)
            unchanged = board.card_by_id("DEPS-GATED")
            self.assertEqual(unchanged.action, "Product",
                             "deps-gated card must not be flipped to Blocked by teamlead")

    def test_block_allowed_when_dependencies_are_done(self):
        """Legit human-escalation path still works: if all deps are Done,
        teamlead may genuinely raise a block for human review."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = self._board(tmp)
            dep = KanbanCard(id="DEP-OK", stage="8_Done", action=Action.DONE)
            card = KanbanCard(
                id="NEEDS-HUMAN", stage="4_Coding", action=Action.CODING,
                dependencies=["DEP-OK"],
            )
            _write(tasks_dir / "8_Done" / "DEP-OK.md", dep)
            _write(tasks_dir / "4_Coding" / "NEEDS-HUMAN.md", card)
            board.refresh(force=True)

            ctx = ActionContext(
                board=board,
                params={"card_id": "NEEDS-HUMAN", "action": "Blocked"},
                reason="design issue needs owner",
                publisher=MagicMock(),
            )
            SetActionHandler().execute(ctx)

            board.refresh(force=True)
            blocked = board.card_by_id("NEEDS-HUMAN")
            self.assertEqual(blocked.action, Action.BLOCKED,
                             "deps-met card should accept a legit Blocked directive")

    def test_non_blocked_transition_untouched(self):
        """Coding → Reviewing should NOT call unblock — no historical spend
        is written off, no sections touched."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = self._board(tmp)
            card = KanbanCard(id="X-3", stage="4_Coding", action=Action.CODING)
            card.body = "# spec\n"
            card.tokens_spent = 1000
            card.tokens_discarded = 0
            _write(tasks_dir / "4_Coding" / "X-3.md", card)
            board.refresh(force=True)

            ctx = ActionContext(
                board=board,
                params={"card_id": "X-3", "action": "Reviewing"},
                reason="ready for review",
                publisher=MagicMock(),
            )
            SetActionHandler().execute(ctx)

            board.refresh(force=True)
            fresh = board.card_by_id("X-3")
            self.assertEqual(fresh.action, Action.REVIEWING)
            self.assertEqual(fresh.tokens_discarded, 0,
                             "no unblock cleanup on normal forward move")


if __name__ == "__main__":
    unittest.main()
