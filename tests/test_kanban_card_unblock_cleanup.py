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


if __name__ == "__main__":
    unittest.main()
