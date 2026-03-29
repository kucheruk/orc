#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.app import App

from orc_core.tui.screens.execution import ExecutionScreen
from orc_core.tui.screens.session_panel import SessionPanel, _format_activity
from orc_core.stream_monitor_state import MetricsStore, MonitorSnapshot


class ExecutionScreenRenderTest(unittest.TestCase):
    def test_activity_markup_shows_starting_before_first_event(self) -> None:
        markup = _format_activity(
            phase="starting", status="no messages yet",
            since=0.0, tool_count=0, is_subagent=False, detail="full",
        )
        self.assertIn("BOOT", markup)
        self.assertIn("no messages yet", markup)

    def test_activity_markup_uses_expected_thresholds(self) -> None:
        markup = _format_activity(
            phase="thinking", status="planning",
            since=time.time() - 1.0, tool_count=0, is_subagent=False, detail="full",
        )
        self.assertIn("THINK", markup)

        markup = _format_activity(
            phase="waiting", status="waiting",
            since=time.time() - 20.0, tool_count=0, is_subagent=False, detail="full",
        )
        self.assertIn("WAIT", markup)

        markup = _format_activity(
            phase="waiting", status="waiting",
            since=time.time() - 75.0, tool_count=0, is_subagent=False, detail="full",
        )
        self.assertIn("STALL?", markup)

    def test_activity_markup_shows_network_problem_as_red_status(self) -> None:
        markup = _format_activity(
            phase="network_problem", status="Network problems: reconnecting",
            since=time.time() - 5.0, tool_count=0, is_subagent=False, detail="full",
        )
        self.assertIn("NETWORK", markup)
        self.assertIn("[red]", markup)
        self.assertIn("Network problems", markup)

    def test_activity_markup_escapes_live_status_markup_tokens(self) -> None:
        markup = _format_activity(
            phase="assistant", status="responding [/",
            since=time.time() - 1.0, tool_count=0, is_subagent=False, detail="full",
        )
        self.assertIn(r"\[/", markup)

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
        )
        panel = SessionPanel(session_id="s1", id="panel_s1")

        class _TestApp(App[None]):
            def compose(self):
                yield panel

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                panel.update_from_snapshot(snapshot)
                self.assertEqual(panel.task_title, "TASK-1")
                self.assertEqual(panel.progress_done, 1)
                self.assertEqual(panel.progress_total, 4)
                self.assertEqual(panel.total_lines, 10)
                self.assertEqual(panel.progress_remaining, 3)
                self.assertEqual(panel.progress_added_delta, 2)
                activity = panel.query_one("#activity_label_s1")
                self.assertIn("AGENT", str(activity.render()))
                task_label = panel.query_one("#task_label_s1")
                self.assertIn("Progress: 1/4", str(task_label.render()))
                self.assertIn("(+2)", str(task_label.render()))
                stats = panel.query_one("#stats_label_s1")
                self.assertIn("Done: 1", str(stats.render()))
                self.assertIn("Ahead: 3", str(stats.render()))
                self.assertIn("Total: 4", str(stats.render()))
                self.assertIn("+7", str(stats.render()))
                self.assertIn("-2", str(stats.render()))

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
        panel = SessionPanel(session_id="s1", id="panel_s1")

        class _TestApp(App[None]):
            def compose(self):
                yield panel

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                panel.update_from_snapshot(snapshot)
                task_label = panel.query_one("#task_label_s1")
                self.assertNotIn("(+", str(task_label.render()))

        import asyncio

        asyncio.run(_run())

    def test_mode_label_shows_quit_after_task_mode(self) -> None:
        panel = SessionPanel(session_id="s1", id="panel_s1")

        class _TestApp(App[None]):
            def compose(self):
                yield panel

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                panel.set_quit_after_task_requested(True)
                mode = panel.query_one("#mode_label_s1")
                self.assertIn("QUIT AFTER TASK", str(mode.render()))
                panel.set_quit_after_task_requested(False)
                self.assertIn("Mode: normal", str(mode.render()))

        import asyncio

        asyncio.run(_run())

    def test_task_label_includes_markdown_heading_after_progress(self) -> None:
        metrics = MetricsStore(tokens_total=1, files_edited=1, command_count=1, total_lines=1, total_output_chars=1)
        snapshot = MonitorSnapshot(
            task_id="WEB-020",
            started_at=time.time() - 5,
            progress_done=164,
            progress_total=184,
            metrics=metrics,
            last_event_type="assistant",
            last_event_note="ok",
            recent_commands=[],
            recent_files=[],
            recent_events=[],
            reasoning_lines=[],
            spinner_idx=0,
            last_event_at=time.time() - 1,
            progress_remaining=20,
            progress_added_delta=0,
            eta_seconds=None,
        )
        panel = SessionPanel(session_id="s1", id="panel_s1")

        class _TestApp(App[None]):
            def compose(self):
                yield panel

        async def _run() -> None:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tasks_dir = Path(tmp_dir) / "tasks"
                tasks_dir.mkdir(parents=True, exist_ok=True)
                (tasks_dir / "WEB-020.md").write_text(
                    "# WEB-020\n\nСделать вывод title в статусной строке\n",
                    encoding="utf-8",
                )
                prev_cwd = os.getcwd()
                try:
                    os.chdir(tmp_dir)
                    async with _TestApp().run_test() as pilot:
                        _ = pilot
                        panel.update_from_snapshot(snapshot)
                        task_label = panel.query_one("#task_label_s1")
                        rendered = str(task_label.render())
                        self.assertIn("Progress: 164/184", rendered)
                        self.assertIn("Сделать вывод title в статусной строке", rendered)
                finally:
                    os.chdir(prev_cwd)

        import asyncio

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
