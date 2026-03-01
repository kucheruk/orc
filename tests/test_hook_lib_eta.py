#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import tempfile
import unittest
from pathlib import Path

from orc_core.hooks import ensure_repo_hooks


class HookLibEtaTest(unittest.TestCase):
    def _load_rendered_hook_lib(self):
        tmpdir = tempfile.TemporaryDirectory()
        _, _ = ensure_repo_hooks(tmpdir.name)
        module_path = Path(tmpdir.name) / ".cursor" / "hooks" / "orc_hook_lib.py"
        spec = importlib.util.spec_from_file_location("rendered_orc_hook_lib", module_path)
        if spec is None or spec.loader is None:
            tmpdir.cleanup()
            raise RuntimeError("Failed to load rendered hook lib")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return tmpdir, module

    def test_record_task_duration_is_idempotent_per_task(self) -> None:
        tmpdir, orc_hook_lib = self._load_rendered_hook_lib()
        stats = {"tokens_total": 0}

        updated = orc_hook_lib.record_task_duration(stats, "TASK-1", 75.0)
        updated = orc_hook_lib.record_task_duration(updated, "TASK-1", 120.0)

        self.assertEqual(updated["durations_by_task"]["TASK-1"], 75)
        self.assertEqual(updated["recent_durations"], [75])
        self.assertEqual(updated["active_seconds_total"], 75.0)
        tmpdir.cleanup()

    def test_build_report_uses_last_three_durations_for_eta(self) -> None:
        tmpdir, orc_hook_lib = self._load_rendered_hook_lib()
        stats = {
            "tokens_total": 600,
            "recent_durations": [60, 120, 180, 240],
            "active_seconds_total": 600,
        }

        report = orc_hook_lib.build_report(stats, total_tasks=10, done_tasks=7)

        self.assertEqual(report["tasks_remaining"], 3)
        self.assertEqual(report["eta"], "9m")
        self.assertAlmostEqual(report["tasks_per_hour"], 20.0)
        self.assertAlmostEqual(report["tokens_per_min"], 60.0)
        tmpdir.cleanup()

    def test_build_report_returns_unknown_eta_without_duration_history(self) -> None:
        tmpdir, orc_hook_lib = self._load_rendered_hook_lib()
        stats = {"tokens_total": 100, "active_seconds_total": 120}

        report = orc_hook_lib.build_report(stats, total_tasks=5, done_tasks=3)

        self.assertEqual(report["tasks_remaining"], 2)
        self.assertEqual(report["eta"], "unknown")
        self.assertEqual(report["tasks_per_hour"], 0.0)
        tmpdir.cleanup()

    def test_running_time_uses_active_seconds_not_wall_clock_started_at(self) -> None:
        tmpdir, orc_hook_lib = self._load_rendered_hook_lib()
        stats = {
            "started_at": "2000-01-01T00:00:00",
            "tokens_total": 0,
            "active_seconds_total": 120,
            "recent_durations": [60, 60, 60],
        }

        report = orc_hook_lib.build_report(stats, total_tasks=3, done_tasks=1)

        self.assertEqual(report["running_time"], "2m")
        tmpdir.cleanup()


if __name__ == "__main__":
    unittest.main()
