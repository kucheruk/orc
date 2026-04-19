#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.hook_scripts import hook_reporter


class HookReporterEtaTest(unittest.TestCase):
    def test_record_task_duration_is_idempotent_per_task(self) -> None:
        stats = {"tokens_total": 0}

        updated = hook_reporter.record_task_duration(stats, "TASK-1", 75.0)
        updated = hook_reporter.record_task_duration(updated, "TASK-1", 120.0)

        self.assertEqual(updated["durations_by_task"]["TASK-1"], 75)
        self.assertEqual(updated["recent_durations"], [75])
        self.assertEqual(updated["active_seconds_total"], 75.0)

    def test_build_report_uses_last_three_durations_for_eta(self) -> None:
        stats = {
            "tokens_total": 600,
            "recent_durations": [60, 120, 180, 240],
            "active_seconds_total": 600,
        }

        report = hook_reporter.build_report(stats, total_tasks=10, done_tasks=7)

        self.assertEqual(report["tasks_remaining"], 3)
        self.assertEqual(report["eta"], "9m")
        self.assertAlmostEqual(report["tasks_per_hour"], 20.0)
        self.assertAlmostEqual(report["tokens_per_min"], 60.0)

    def test_build_report_returns_unknown_eta_without_duration_history(self) -> None:
        stats = {"tokens_total": 100, "active_seconds_total": 120}

        report = hook_reporter.build_report(stats, total_tasks=5, done_tasks=3)

        self.assertEqual(report["tasks_remaining"], 2)
        self.assertEqual(report["eta"], "unknown")
        self.assertEqual(report["tasks_per_hour"], 0.0)

    def test_running_time_uses_active_seconds_not_wall_clock_started_at(self) -> None:
        stats = {
            "started_at": "2000-01-01T00:00:00",
            "tokens_total": 0,
            "active_seconds_total": 120,
            "recent_durations": [60, 60, 60],
        }

        report = hook_reporter.build_report(stats, total_tasks=3, done_tasks=1)

        self.assertEqual(report["running_time"], "2m")


if __name__ == "__main__":
    unittest.main()
