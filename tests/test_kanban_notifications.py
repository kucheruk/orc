#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for kanban notification formatting."""

import unittest

from orc_core.board.kanban_card import KanbanCard
from orc_core.board.stage_constants import STAGE_CODING, STAGE_DONE, STAGE_REVIEW, STAGE_TODO
from orc_core.board.kanban_notifications import extract_card_summary, format_completion_message
from orc_core.notifications.messages import Severity


class FormatCompletionMessageTest(unittest.TestCase):
    def _card(self, **kwargs):
        defaults = dict(id="T-001", title="Fix bug", stage=STAGE_REVIEW, action="reviewing")
        defaults.update(kwargs)
        return KanbanCard(**defaults)

    def test_stage_change_produces_message(self):
        card = self._card(stage=STAGE_REVIEW)
        envelope = format_completion_message(card, "coder", STAGE_CODING, "coding", "standard", 300.0, (5, 1, 10))
        self.assertIsNotNone(envelope)
        severity, msg = envelope
        # Intermediate stage hop: surfaces only in debug notify mode.
        self.assertEqual(severity, Severity.INFO)
        self.assertIn("T-001", msg)
        self.assertIn("Fix bug", msg)
        self.assertIn("5/10", msg)

    def test_done_transition_is_normal_severity(self):
        card = self._card(stage=STAGE_DONE)
        severity, _ = format_completion_message(
            card, "integrator", STAGE_REVIEW, "reviewing", "standard", 120.0, (10, 0, 10),
        )
        self.assertEqual(severity, Severity.NORMAL)

    def test_no_stage_change_returns_none(self):
        card = self._card(stage=STAGE_CODING)
        envelope = format_completion_message(card, "coder", STAGE_CODING, "coding", "standard", 60.0, (1, 0, 5))
        self.assertIsNone(envelope)

    def test_expedite_flag_produces_message(self):
        card = self._card(stage=STAGE_CODING, class_of_service="expedite", cos_justification="urgent")
        envelope = format_completion_message(card, "coder", STAGE_CODING, "coding", "standard", 60.0, (1, 0, 5))
        self.assertIsNotNone(envelope)
        severity, msg = envelope
        self.assertEqual(severity, Severity.NORMAL)
        self.assertIn("EXPEDITE", msg)
        self.assertIn("urgent", msg)

    def test_done_card_includes_summary(self):
        body = "# 1. Spec\nspec\n# 2. Plan\nplan\n# 3. Implementation\nDid great work.\n# 4. Review\n"
        card = self._card(stage=STAGE_DONE, body=body)
        envelope = format_completion_message(card, "integrator", STAGE_REVIEW, "reviewing", "standard", 120.0, (10, 0, 10))
        self.assertIsNotNone(envelope)
        _, msg = envelope
        self.assertIn("Did great work.", msg)

    def test_action_change_shown(self):
        card = self._card(stage=STAGE_REVIEW, action="reviewing")
        _, msg = format_completion_message(card, "coder", STAGE_CODING, "coding", "standard", 60.0, (1, 0, 5))
        self.assertIn("coding", msg)
        self.assertIn("reviewing", msg)


class ExtractCardSummaryTest(unittest.TestCase):
    def test_extracts_section3(self):
        card = KanbanCard(id="T-001", body="# 3. Notes\nFirst para\n\nSecond para\n# 4. End\n")
        self.assertEqual(extract_card_summary(card), "Second para")

    def test_empty_body(self):
        card = KanbanCard(id="T-001", body="")
        self.assertEqual(extract_card_summary(card), "")

    def test_no_section3(self):
        card = KanbanCard(id="T-001", body="# 1. Spec\nSome text\n")
        self.assertEqual(extract_card_summary(card), "")

    def test_truncates_long_summary(self):
        long_text = "x" * 600
        card = KanbanCard(id="T-001", body=f"# 3. Notes\n{long_text}\n")
        result = extract_card_summary(card)
        self.assertLessEqual(len(result), 500)
        self.assertTrue(result.endswith("..."))


if __name__ == "__main__":
    unittest.main()
