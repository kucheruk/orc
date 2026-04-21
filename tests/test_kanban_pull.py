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

    def test_estimate_frontier_prioritizes_unblockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="E-HIGH", stage="2_Estimate", action="Architect", value_score=95, effort_score=10))
            _add(td, KanbanCard(id="E-UNBLOCK", stage="2_Estimate", action="Architect", value_score=30, effort_score=20))
            _add(td, KanbanCard(id="D-1", stage="2_Estimate", action="Coding", dependencies=["E-UNBLOCK"]))
            _add(td, KanbanCard(id="D-2", stage="2_Estimate", action="Coding", dependencies=["E-UNBLOCK"]))
            board = KanbanBoard(td, repo=FsCardRepository())
            result = find_next_work(board)
            self.assertIsNotNone(result)
            self.assertEqual(result.card.id, "E-UNBLOCK")
            self.assertEqual(result.role, ROLE_ARCHITECT)

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

    def test_blocked_cards_are_not_arbitrated(self):
        """Blocked is a terminal state for human intervention —
        arbitrating it via the teamlead AI just burns tokens on the same
        "needs human" decision every tick. blocked_sweep still alerts
        the operator; AI arbitration doesn't run for blocked cards."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="B-1", stage="5_Review", action="Blocked"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board)
            self.assertIsNone(card,
                              "find_teamlead_work must not surface blocked "
                              "cards for AI arbitration")

    def test_no_teamlead_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="OK-1", stage="4_Coding", action="Coding", loop_count=0))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board)
            self.assertIsNone(card)

    def test_finds_arbitration_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="A-1", stage="4_Coding", action="Arbitration", loop_count=1))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board)
            self.assertIsNotNone(card)
            self.assertEqual(card.id, "A-1")

    def test_arbitration_requested_picked_over_blocked(self):
        """When a card explicitly asks for arbitration and another is
        blocked, the arbitration-requested card wins — blocked cards
        sit out of the teamlead work queue entirely."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="A-1", stage="4_Coding", action="Arbitration", loop_count=1))
            _add(td, KanbanCard(id="B-1", stage="5_Review", action="Blocked"))
            board = KanbanBoard(td, repo=FsCardRepository())
            card = find_teamlead_work(board)
            self.assertIsNotNone(card)
            self.assertEqual(card.id, "A-1")


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


class TestOrphanedBudgetGrowth(unittest.TestCase):
    """Non-BLOCKED exhausted cards must get their budget grown so pick_best sees them."""

    def test_non_blocked_exhausted_card_gets_budget_grown(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(
                id="OB-1", stage="5_Review", action="Reviewing",
                effort_score=64,
                tokens_spent=400_000, token_budget=320_000,
            ))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            card = board.card_by_id("OB-1")
            self.assertEqual(card.action, "Reviewing")
            # tokens_spent is preserved — cumulative stats file would restore it anyway.
            self.assertEqual(card.tokens_spent, 400_000)
            # token_budget grew by effort_score * TOKENS_PER_EFFORT_POINT (64 * 10000 = 640000).
            self.assertEqual(card.token_budget, 320_000 + 640_000)
            self.assertFalse(card.is_budget_exhausted)

    def test_blocked_exhausted_card_is_not_touched(self):
        """Blocked cards stay exhausted until teamlead explicitly unblocks them."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(
                id="OB-2", stage="5_Review", action="Blocked",
                effort_score=64,
                tokens_spent=400_000, token_budget=320_000,
            ))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            card = board.card_by_id("OB-2")
            self.assertEqual(card.tokens_spent, 400_000)
            self.assertEqual(card.token_budget, 320_000)
            self.assertTrue(card.is_budget_exhausted)

    def test_sweep_is_idempotent(self):
        """Running find_next_work twice must not double-bump the budget."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(
                id="OB-3", stage="5_Review", action="Reviewing",
                effort_score=64,
                tokens_spent=400_000, token_budget=320_000,
            ))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)
            budget_after_first = board.card_by_id("OB-3").token_budget
            find_next_work(board)
            budget_after_second = board.card_by_id("OB-3").token_budget

            self.assertEqual(budget_after_first, budget_after_second,
                             "Second sweep must be a no-op (card no longer exhausted).")


class TestAutoArchiveDecomposedParents(unittest.TestCase):
    """find_next_work must retire parent cards whose sub-cards already exist.

    Otherwise the architect keeps re-pulling the parent and burns tokens in
    a decomposition death-loop.
    """

    def test_parent_with_sub_cards_gets_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            # Parent sits in Estimate with action=Architect, pulled for estimation.
            _add(td, KanbanCard(id="FILE-001", stage="2_Estimate", action="Architect"))
            # Architect already decomposed it into three sub-cards.
            _add(td, KanbanCard(id="FILE-001-A", stage="2_Estimate", action="Product",
                                 effort_score=30))
            _add(td, KanbanCard(id="FILE-001-B", stage="2_Estimate", action="Product",
                                 effort_score=30))
            _add(td, KanbanCard(id="FILE-001-C", stage="2_Estimate", action="Product",
                                 effort_score=30))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            parent = board.card_by_id("FILE-001")
            self.assertEqual(parent.stage, "8_Done",
                             "Decomposed parent must be auto-archived to STAGE_DONE.")
            # Sub-cards remain untouched.
            self.assertEqual(board.card_by_id("FILE-001-A").stage, "2_Estimate")
            self.assertEqual(board.card_by_id("FILE-001-B").stage, "2_Estimate")
            self.assertEqual(board.card_by_id("FILE-001-C").stage, "2_Estimate")

    def test_parent_without_sub_cards_is_not_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="PLAIN-001", stage="2_Estimate", action="Architect"))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            self.assertEqual(board.card_by_id("PLAIN-001").stage, "2_Estimate")

    def test_compound_id_without_subcards_is_not_falsely_matched(self):
        """`NOTIF-005` must not be mistaken for a sub-card of `NOTIF`."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            # 3-letter suffix — not the A/B/C shape auto-archive expects.
            _add(td, KanbanCard(id="X-001", stage="2_Estimate", action="Architect"))
            _add(td, KanbanCard(id="X-001-REDO", stage="2_Estimate", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            # X-001 should NOT be archived; X-001-REDO is not a sub-card (suffix is multi-letter).
            self.assertEqual(board.card_by_id("X-001").stage, "2_Estimate")

    def test_does_not_re_archive_already_done_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="OLD-001", stage="8_Done", action="Done"))
            _add(td, KanbanCard(id="OLD-001-A", stage="2_Estimate", action="Product"))
            board = KanbanBoard(td, repo=FsCardRepository())

            # Should be a no-op — no exception, parent stays in Done.
            find_next_work(board)

            self.assertEqual(board.card_by_id("OLD-001").stage, "8_Done")

    def test_dep_broken_todo_card_is_demoted_to_estimate(self):
        """Cards in 3_Todo/Coding whose deps became unmet after a
        dependency rewire must be sent back to 2_Estimate so the Todo
        slot is free for ready cards. Without this, all Todo slots can
        fill with unpickable cards and worker slots sit idle even when
        the Estimate queue has Product/Architect work waiting
        (jeeves 2026-04-20 scenario).
        """
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            # UPSTREAM sits in Estimate — its dep chain isn't ready yet.
            _add(td, KanbanCard(id="UPSTREAM", stage="2_Estimate", action="Product"))
            # DOWNSTREAM was promoted to Todo earlier (when UPSTREAM was
            # Done), but a subsequent decomposition rewired its dep back
            # onto UPSTREAM. Now it sits in Todo with unmet deps.
            _add(td, KanbanCard(
                id="DOWNSTREAM", stage="3_Todo", action="Coding",
                dependencies=["UPSTREAM"],
            ))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            demoted = board.card_by_id("DOWNSTREAM")
            self.assertEqual(demoted.stage, "2_Estimate",
                             "dep-broken Todo card must be demoted back to Estimate")
            self.assertEqual(demoted.action, "Coding",
                             "action preserved so _auto_promote_estimate can repromote once deps clear")

    def test_demote_skips_cards_already_moved_out_of_todo(self):
        """`cards_with_action(STAGE_TODO, Action.CODING)` can return a
        stale snapshot — a concurrent tick may have moved the card out of
        Todo between the scan and the demote call. Calling `move_card` on
        a card that is already in Estimate trips the "must move right"
        guard and crashes the worker (jeeves INC-001 2026-04-21:
        QA-003-B crash-killed s2 with
        `Cannot move card QA-003-B from 2_Estimate to 2_Estimate`)."""
        from orc_core.board.kanban_pull import _demote_dep_broken_todo

        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="UPSTREAM", stage="2_Estimate", action="Product"))
            _add(td, KanbanCard(
                id="STALE", stage="3_Todo", action="Coding",
                dependencies=["UPSTREAM"],
            ))
            board = KanbanBoard(td, repo=FsCardRepository())

            # Prime the index so the snapshot knows about STALE-in-Todo.
            list(board.cards_with_action("3_Todo", "Coding"))

            # Simulate the concurrent-tick race: another code path has
            # already moved STALE back to Estimate. An in-memory mutation
            # reproduces the state that triggered the jeeves crash —
            # `board.move_card` would first go through the legitimate
            # Todo→Estimate transition here.
            stale_card = board.card_by_id("STALE")
            stale_card.stage = "2_Estimate"

            # Now the demote sweep runs. Without the skip it tries to
            # move STALE from Estimate to Estimate and raises.
            try:
                _demote_dep_broken_todo(board)
            except ValueError as exc:
                self.fail(f"_demote_dep_broken_todo must skip already-moved "
                          f"cards instead of raising: {exc!r}")

    def test_todo_card_with_met_deps_is_not_demoted(self):
        """Must not demote cards whose deps are genuinely ready.
        A card with met deps either stays in Todo or gets picked up
        by a coder (advancing forward) — but must never slide back
        to Estimate."""
        with tempfile.TemporaryDirectory() as tmp:
            td, _ = _setup(tmp)
            _add(td, KanbanCard(id="UP-OK", stage="8_Done", action="Done"))
            _add(td, KanbanCard(
                id="READY", stage="3_Todo", action="Coding",
                dependencies=["UP-OK"],
            ))
            board = KanbanBoard(td, repo=FsCardRepository())

            find_next_work(board)

            # Card should NOT have regressed to Estimate; may have advanced
            # to Coding if a coder slot picked it up during find_next_work.
            final = board.card_by_id("READY")
            self.assertNotEqual(final.stage, "2_Estimate",
                                "met-deps card must never regress to Estimate")


if __name__ == "__main__":
    unittest.main()
