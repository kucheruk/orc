#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from orc_core.stream_monitor import StreamJsonMonitor


class StreamMonitorFormattingTest(unittest.TestCase):
    def test_reasoning_chunks_are_coalesced_without_word_split(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.append_reasoning_fragment("Prior")
        state.append_reasoning_fragment("itizing user commit preference")

        self.assertEqual(len(state._recent_reasoning), 1)
        self.assertEqual(state._recent_reasoning[-1], "Prioritizing user commit preference")

    def test_reasoning_strips_basic_markdown(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event = {"type": "assistant", "subtype": "reasoning"}
        state._remember_reasoning(event, "**Checking for existing technical specs**")

        self.assertEqual(len(state._recent_reasoning), 1)
        self.assertNotIn("**", state._recent_reasoning[-1])
        self.assertEqual(state._recent_reasoning[-1], "Checking for existing technical specs")

    def test_reasoning_panel_lines_wrap_long_entries(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state._recent_reasoning.append("Assessing documentation and code structure for event feed improvements and token parsing stability")

        lines = state.reasoning_lines_for_panel(max_width=40, max_lines=5)
        self.assertGreater(len(lines), 1)

    def test_event_summary_contains_useful_context(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        summary = state._summarize_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_name": "ReadFile",
            },
            "",
        )

        self.assertIn("tool_call:started", summary)
        self.assertIn("ReadFile", summary)

    def test_maybe_report_updates_state_and_requests_render(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor.log_path = Path("/tmp/orc.log")
        monitor.metrics = SimpleNamespace(tokens_total=None, total_lines=0, command_count=0, files_edited=None)
        monitor._report_interval = 0.0
        monitor._last_report_time = 0.0
        monitor._last_git_stats_time = 0.0
        monitor._state = MagicMock()
        monitor._screen = MagicMock()
        monitor._update_git_stats = lambda: None
        monitor._write_metrics_snapshot = lambda: None
        monitor.task_id = "TASK-1"

        monitor.maybe_report()
        monitor._state.tick_spinner.assert_called_once()
        monitor._screen.request_render.assert_called_once()


if __name__ == "__main__":
    unittest.main()
