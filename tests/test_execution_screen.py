#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import unittest

from textual.app import App

from orc_core.tui.screens.execution import ExecutionScreen
from orc_core.stream_monitor_state import MetricsStore, MonitorSnapshot


class ExecutionScreenRenderTest(unittest.TestCase):
    def test_activity_markup_uses_expected_thresholds(self) -> None:
        screen = ExecutionScreen()
        self.assertIn("active now", screen._activity_markup(1.0))
        self.assertIn("waiting", screen._activity_markup(20.0))
        self.assertIn("idle", screen._activity_markup(75.0))

    def test_render_text_contains_key_sections(self) -> None:
        metrics = MetricsStore(tokens_total=42, files_edited=3, command_count=5, total_lines=10, total_output_chars=999)
        snapshot = MonitorSnapshot(
            task_id="TASK-1",
            started_at=time.time() - 5,
            progress_done=1,
            progress_total=4,
            metrics=metrics,
            last_event_type="tool_call",
            last_event_note="ReadFile started",
            recent_commands=["ReadFile", "Shell"],
            recent_files=["/tmp/a.py"],
            recent_events=["tool_call:started ReadFile"],
            reasoning_lines=["planning step one"],
            spinner_idx=1,
            last_event_at=time.time() - 3,
        )
        screen = ExecutionScreen()

        class _TestApp(App[None]):
            def compose(self):
                yield screen

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                screen.update_from_snapshot(snapshot)
                self.assertEqual(screen.task_title, "Task: TASK-1")
                self.assertEqual(screen.progress_done, 1)
                self.assertEqual(screen.progress_total, 4)
                self.assertEqual(screen.total_lines, 10)
                activity = screen.query_one("#activity_label")
                self.assertIn("Agent activity", str(activity.render()))

        import asyncio

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
