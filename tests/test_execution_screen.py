#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.app import App

from orc_core.tui.screens.execution import ExecutionScreen
from orc_core.stream_monitor_state import MetricsStore, MonitorSnapshot


class ExecutionScreenRenderTest(unittest.TestCase):
    def test_activity_markup_shows_starting_before_first_event(self) -> None:
        screen = ExecutionScreen()
        starting = screen._activity_markup()
        self.assertIn("BOOT", starting)
        self.assertIn("no messages yet", starting)

    def test_activity_markup_uses_expected_thresholds(self) -> None:
        screen = ExecutionScreen()
        screen.live_phase = "thinking"
        screen.live_status = "planning"
        screen.live_since = time.time() - 1.0
        self.assertIn("THINK", screen._activity_markup())

        screen.live_phase = "waiting"
        screen.live_status = "waiting"
        screen.live_since = time.time() - 20.0
        self.assertIn("WAIT", screen._activity_markup())

        screen.live_since = time.time() - 75.0
        self.assertIn("STALL?", screen._activity_markup())

    def test_render_text_contains_key_sections(self) -> None:
        metrics = MetricsStore(
            tokens_total=42,
            files_edited=3,
            command_count=5,
            total_lines=10,
            total_output_chars=999,
            git_added=7,
            git_deleted=2,
        )
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
            progress_remaining=3,
            progress_added_delta=2,
            eta_seconds=180.0,
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
                self.assertEqual(screen.progress_remaining, 3)
                self.assertEqual(screen.progress_added_delta, 2)
                activity = screen.query_one("#activity_label")
                self.assertIn("AGENT", str(activity.render()))
                task_label = screen.query_one("#task_label")
                self.assertIn("Progress: 1/4", str(task_label.render()))
                self.assertIn("(+2)", str(task_label.render()))
                stats = screen.query_one("#stats_label")
                self.assertIn("Done: 1", str(stats.render()))
                self.assertIn("Ahead: 3", str(stats.render()))
                self.assertIn("Total: 4", str(stats.render()))
                self.assertIn("+7", str(stats.render()))
                self.assertIn("-2", str(stats.render()))

        import asyncio

        asyncio.run(_run())

    def test_debug_log_label_shows_file_name_when_available(self) -> None:
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
            with patch(
                "orc_core.tui.screens.execution.get_debug_log_path",
                return_value=Path("/tmp/orc/orc-debug-20260301-120000-123.jsonl"),
            ):
                async with _TestApp().run_test() as pilot:
                    _ = pilot
                    screen.update_from_snapshot(snapshot)
                    stats = screen.query_one("#stats_label")
                    self.assertNotIn("/tmp/orc/orc-debug-20260301-120000-123.jsonl", str(stats.render()))
                    debug_log_label = screen.query_one("#debug_log_label")
                    self.assertIn("Debug log: orc-debug-20260301-120000-123.jsonl", str(debug_log_label.render()))

        import asyncio

        asyncio.run(_run())

    def test_task_label_hides_backlog_delta_when_zero(self) -> None:
        metrics = MetricsStore(tokens_total=1, files_edited=1, command_count=1, total_lines=1, total_output_chars=1)
        snapshot = MonitorSnapshot(
            task_id="TASK-1",
            started_at=time.time() - 5,
            progress_done=1,
            progress_total=2,
            metrics=metrics,
            last_event_type="assistant",
            last_event_note="ok",
            recent_commands=[],
            recent_files=[],
            recent_events=[],
            reasoning_lines=[],
            spinner_idx=0,
            last_event_at=time.time() - 1,
            progress_remaining=1,
            progress_added_delta=0,
            eta_seconds=None,
        )
        screen = ExecutionScreen()

        class _TestApp(App[None]):
            def compose(self):
                yield screen

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                screen.update_from_snapshot(snapshot)
                task_label = screen.query_one("#task_label")
                self.assertNotIn("(+", str(task_label.render()))

        import asyncio

        asyncio.run(_run())

    def test_mode_label_shows_quit_after_task_mode(self) -> None:
        screen = ExecutionScreen()

        class _TestApp(App[None]):
            def compose(self):
                yield screen

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                screen.set_quit_after_task_requested(True)
                mode = screen.query_one("#mode_label")
                self.assertIn("QUIT AFTER TASK", str(mode.render()))
                screen.set_quit_after_task_requested(False)
                self.assertIn("Mode: normal", str(mode.render()))

        import asyncio

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
