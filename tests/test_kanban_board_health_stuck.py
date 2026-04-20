#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for stuck-card detection and HealthCheckStep bootstrap.

These cover two token-burn patterns observed in production:
1. HealthCheckStep fired on the very first teamlead iteration because
   _last_check was zero-seeded, invoking a full AI teamlead prompt before
   any work had been attempted.
2. detect_stuck_cards flagged backlog cards (Estimate/Todo) as stuck based
   on their creation timestamp, which is normal waiting, not a pathology.
"""

import time
import unittest
from datetime import datetime, timedelta, timezone

from orc_core.agents.runners.teamlead_steps import HealthCheckStep
from orc_core.board.kanban_board_health import detect_stuck_cards
from orc_core.board.kanban_card import KanbanCard


def _card(id: str, stage: str, updated_minutes_ago: int) -> KanbanCard:
    ts = datetime.now(timezone.utc) - timedelta(minutes=updated_minutes_ago)
    return KanbanCard(id=id, stage=stage, updated_at=ts.isoformat())


class TestDetectStuckCardsStageScope(unittest.TestCase):
    def test_estimate_backlog_card_is_not_stuck(self):
        cards = [_card("A-1", "2_Estimate", updated_minutes_ago=6000)]
        self.assertEqual(detect_stuck_cards(cards, done_ids=set()), "")

    def test_todo_queue_card_is_not_stuck(self):
        cards = [_card("A-2", "3_Todo", updated_minutes_ago=6000)]
        self.assertEqual(detect_stuck_cards(cards, done_ids=set()), "")

    def test_coding_card_idle_beyond_threshold_is_stuck(self):
        cards = [_card("A-3", "4_Coding", updated_minutes_ago=6000)]
        summary = detect_stuck_cards(cards, done_ids=set())
        self.assertIn("A-3", summary)
        self.assertIn("4_Coding", summary)

    def test_review_card_idle_beyond_threshold_is_stuck(self):
        cards = [_card("A-4", "5_Review", updated_minutes_ago=6000)]
        self.assertIn("A-4", detect_stuck_cards(cards, done_ids=set()))

    def test_testing_card_idle_beyond_threshold_is_stuck(self):
        cards = [_card("A-5", "6_Testing", updated_minutes_ago=6000)]
        self.assertIn("A-5", detect_stuck_cards(cards, done_ids=set()))

    def test_handoff_card_idle_beyond_threshold_is_stuck(self):
        cards = [_card("A-6", "7_Handoff", updated_minutes_ago=6000)]
        self.assertIn("A-6", detect_stuck_cards(cards, done_ids=set()))

    def test_assigned_card_skipped_even_in_active_stage(self):
        card = _card("A-7", "4_Coding", updated_minutes_ago=6000)
        card.assigned_agent = "s2"
        self.assertEqual(detect_stuck_cards([card], done_ids=set()), "")

    def test_card_with_unmet_deps_skipped(self):
        card = _card("A-8", "4_Coding", updated_minutes_ago=6000)
        card.dependencies = ["B-9"]
        self.assertEqual(detect_stuck_cards([card], done_ids=set()), "")

    def test_done_stage_is_not_stuck(self):
        cards = [_card("A-9", "8_Done", updated_minutes_ago=6000)]
        self.assertEqual(detect_stuck_cards(cards, done_ids={"A-9"}), "")


class TestHealthCheckStepBootstrap(unittest.TestCase):
    def test_first_check_is_not_immediately_due(self):
        """A freshly constructed step must not fire on the very first tick.
        Otherwise every ORC startup burns a full teamlead AI call before
        workers have a chance to actually attempt work."""
        step = HealthCheckStep()
        self.assertFalse(step.due(), "HealthCheckStep.due() must be False on init")

    def test_check_becomes_due_after_base_interval(self):
        step = HealthCheckStep()
        step._last_check = time.time() - (HealthCheckStep._BASE_INTERVAL + 1)
        self.assertTrue(step.due())


if __name__ == "__main__":
    unittest.main()
