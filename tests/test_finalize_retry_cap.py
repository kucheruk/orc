#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the finalize retry cap in finalize_completed_worktree."""

from __future__ import annotations

import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from orc_core.board.action_constants import Action
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.stage_constants import STAGE_DONE, STAGE_HANDOFF
from orc_core.git.use_cases.finalize_task_worktree import (
    MAX_FINALIZE_RETRIES,
    finalize_completed_worktree,
)


def _make_card(task_id: str = "T-1") -> KanbanCard:
    card = KanbanCard(id=task_id, title="t", stage=STAGE_HANDOFF, action=Action.DONE)
    return card


def _fake_board() -> MagicMock:
    board = MagicMock()
    board.move_card = MagicMock()
    board.save_card = MagicMock()
    return board


def _fake_publisher() -> MagicMock:
    pub = MagicMock()
    pub.emit = MagicMock()
    return pub


class FinalizeRetryCapTest(unittest.TestCase):
    def test_first_failure_flips_action_to_integrating(self) -> None:
        card = _make_card()
        integrator = MagicMock()
        integrator.integrate.return_value = False

        result = finalize_completed_worktree(
            card=card,
            worktree=None,
            slot=None,
            board=_fake_board(),
            integrator=integrator,
            cleanup_fn=MagicMock(),
            log_path=Path("/tmp/orc.log"),
            main_branch="main",
            publisher=_fake_publisher(),
            worktree_lock=threading.Lock(),
        )

        self.assertFalse(result)
        self.assertEqual(card.action, Action.INTEGRATING)
        self.assertEqual(card.finalize_retries, 1)

    def test_cap_blocks_card_and_stops_retry_loop(self) -> None:
        card = _make_card()
        card.finalize_retries = MAX_FINALIZE_RETRIES - 1  # one more attempt triggers the cap
        integrator = MagicMock()
        integrator.integrate.return_value = False
        publisher = _fake_publisher()

        result = finalize_completed_worktree(
            card=card,
            worktree=None,
            slot=None,
            board=_fake_board(),
            integrator=integrator,
            cleanup_fn=MagicMock(),
            log_path=Path("/tmp/orc.log"),
            main_branch="main",
            publisher=publisher,
            worktree_lock=threading.Lock(),
        )

        self.assertFalse(result)
        # Card is parked for human review, not flipped back to Integrating.
        self.assertEqual(card.action, Action.BLOCKED)
        self.assertEqual(card.finalize_retries, MAX_FINALIZE_RETRIES)
        # An escalate event must surface the cap for the operator.
        escalate_calls = [c for c in publisher.emit.call_args_list if c.args and c.args[0] == "escalate"]
        self.assertTrue(escalate_calls, "expected at least one escalate emit")

    def test_unblock_resets_retry_counter(self) -> None:
        card = _make_card()
        card.finalize_retries = MAX_FINALIZE_RETRIES
        card.action = Action.BLOCKED

        card.unblock()

        self.assertEqual(card.finalize_retries, 0)
        self.assertEqual(card.action, Action.CODING)

    def test_success_moves_card_to_done_and_skips_counter(self) -> None:
        card = _make_card()
        card.finalize_retries = 1  # prior failure counted
        integrator = MagicMock()
        integrator.integrate.return_value = True
        board = _fake_board()

        result = finalize_completed_worktree(
            card=card,
            worktree=None,
            slot=None,
            board=board,
            integrator=integrator,
            cleanup_fn=MagicMock(),
            log_path=Path("/tmp/orc.log"),
            main_branch="main",
            publisher=_fake_publisher(),
            worktree_lock=threading.Lock(),
        )

        self.assertTrue(result)
        board.move_card.assert_called_once()
        # Counter does not need to be reset on success — card leaves Handoff.
        self.assertEqual(card.finalize_retries, 1)


if __name__ == "__main__":
    unittest.main()
