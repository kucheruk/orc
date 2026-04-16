#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.tasks.completion.outcomes import TaskOutcomeTracker


class TaskOutcomeTrackerTest(unittest.TestCase):
    def test_applied_result_runs_are_idempotent_and_capped(self):
        tracker = TaskOutcomeTracker(applied_result_runs=["run-0"])
        self.assertTrue(tracker.has_applied_result("run-0"))
        self.assertFalse(tracker.record_applied_result("run-0"))

        self.assertTrue(tracker.record_applied_result("run-1", limit=2))
        self.assertTrue(tracker.record_applied_result("run-2", limit=2))
        self.assertFalse(tracker.has_applied_result("run-0"))

        snapshot = tracker.state_snapshot()
        self.assertEqual(snapshot["applied_result_runs"], ["run-1", "run-2"])

    def test_empty_run_id_is_rejected(self):
        tracker = TaskOutcomeTracker()
        with self.assertRaises(ValueError):
            tracker.record_applied_result("")


if __name__ == "__main__":
    unittest.main()
