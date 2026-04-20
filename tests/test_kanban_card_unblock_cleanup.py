#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: unblock must strip prior `## Block Reason` sections.

Every block/unblock cycle appends `## Block Reason\\n<reason>\\n` to the
card body (see KanbanCard.block). Before this fix, unblock never
cleaned it up, so after even two block/unblock cycles the card carried
stale reasons that every subsequent coder/reviewer prompt had to drag
along — pure token burn, and noise the agent has to read past.
"""

import unittest

from orc_core.board.action_constants import Action
from orc_core.board.kanban_card import KanbanCard


class TestUnblockStripsBlockReason(unittest.TestCase):
    def _card_with_body(self, body: str) -> KanbanCard:
        c = KanbanCard(id="T-1", title="t")
        c.body = body
        return c

    def test_single_block_reason_is_stripped_on_unblock(self):
        card = self._card_with_body(
            "# 1. Product Requirements\n\nGoal.\n\n"
            "## Block Reason\nagent returned: max_restarts_exceeded\n"
        )
        card.block("another reason")
        card.unblock()
        self.assertNotIn("Block Reason", card.body)
        self.assertIn("Product Requirements", card.body)
        self.assertEqual(card.action, Action.CODING)

    def test_multiple_accumulated_block_reasons_are_all_stripped(self):
        card = self._card_with_body(
            "# 1. Product Requirements\n\nGoal.\n\n"
            "## Block Reason\nfirst\n\n"
            "## Block Reason\nsecond\n\n"
            "## Block Reason\nthird\n"
        )
        card.unblock()
        self.assertNotIn("Block Reason", card.body)
        self.assertIn("Product Requirements", card.body)

    def test_human_directive_preserved_alongside_strip(self):
        card = self._card_with_body(
            "# 1. Product Requirements\n\nGoal.\n\n"
            "## Human Directive\nlook at x\n\n"
            "## Block Reason\nstale\n"
        )
        card.unblock()
        self.assertIn("Human Directive", card.body)
        self.assertIn("look at x", card.body)
        self.assertNotIn("Block Reason", card.body)

    def test_new_human_directive_appended_after_strip(self):
        card = self._card_with_body(
            "# 1. Product Requirements\n\nGoal.\n\n"
            "## Block Reason\nstale\n"
        )
        card.unblock("try rerunning the finalize step")
        self.assertNotIn("Block Reason", card.body)
        self.assertIn("## Human Directive", card.body)
        self.assertIn("try rerunning the finalize step", card.body)

    def test_body_without_block_reason_is_not_mangled(self):
        original = "# 1. Product Requirements\n\nJust the spec.\n"
        card = self._card_with_body(original)
        card.unblock()
        self.assertEqual(card.body.strip(), original.strip())

    def test_loop_count_and_finalize_retries_reset(self):
        card = self._card_with_body("# section\n\n## Block Reason\nstale\n")
        card.loop_count = 5
        card.finalize_retries = 3
        card.unblock()
        self.assertEqual(card.loop_count, 0)
        self.assertEqual(card.finalize_retries, 0)

    def test_token_accounting_reset_prevents_ping_pong_block(self):
        """Without this reset, a card whose previous attempt exhausted its
        token_budget would re-exhaust the budget check (tokens_spent_net >=
        token_budget) on the next pick_best and bounce right back to
        Blocked — teamlead arbitration would unblock, ORC would re-block,
        indefinitely. Observed on AUDIT-001-C: budget auto-grew to 190K
        chasing a 258K actual spend, never recovered.

        We can't zero tokens_spent outright because accumulate_card_tokens
        reads the workspace stats file and reloads the historical total
        on the next attempt. Instead, bump tokens_discarded to match
        tokens_spent so tokens_spent_net == 0 but the history is
        preserved.
        """
        card = self._card_with_body("# section\n\n## Block Reason\nstale\n")
        card.tokens_spent = 258652
        card.tokens_discarded = 0
        card.token_budget = 190000  # auto-grown by teamlead
        card.unblock()
        # Historical tokens are preserved for audit — not zeroed.
        self.assertEqual(card.tokens_spent, 258652)
        self.assertEqual(card.tokens_discarded, 258652)
        self.assertEqual(card.tokens_spent_net, 0)
        self.assertEqual(card.token_budget, 0,
                         "token_budget must be reset to 0 so "
                         "update_card_token_budget reconstructs it from "
                         "current effort_score on the next assignment")
        self.assertFalse(card.is_budget_exhausted)

    def test_unblock_never_shrinks_tokens_discarded(self):
        """If tokens_discarded was already higher than tokens_spent (weird
        but possible if a past unblock captured the spend and tokens_spent
        was then zeroed by a manual reset), the bump must be idempotent —
        keep the larger value."""
        card = self._card_with_body("# section\n\n## Block Reason\nstale\n")
        card.tokens_spent = 100
        card.tokens_discarded = 500
        card.unblock()
        self.assertEqual(card.tokens_discarded, 500)


if __name__ == "__main__":
    unittest.main()
