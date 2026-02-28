#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import deque
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orc_core.stream_monitor import StreamJsonMonitor


class StreamMonitorFormattingTest(unittest.TestCase):
    def _make_monitor(self) -> StreamJsonMonitor:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor._recent_reasoning = deque(maxlen=12)
        monitor._recent_events = deque(maxlen=8)
        return monitor

    def test_reasoning_chunks_are_coalesced_without_word_split(self) -> None:
        monitor = self._make_monitor()
        monitor._append_reasoning_fragment("Prior")
        monitor._append_reasoning_fragment("itizing user commit preference")

        self.assertEqual(len(monitor._recent_reasoning), 1)
        self.assertEqual(monitor._recent_reasoning[-1], "Prioritizing user commit preference")

    def test_reasoning_strips_basic_markdown(self) -> None:
        monitor = self._make_monitor()
        event = {"type": "assistant", "subtype": "reasoning"}
        monitor._remember_reasoning(event, "**Checking for existing technical specs**")

        self.assertEqual(len(monitor._recent_reasoning), 1)
        self.assertNotIn("**", monitor._recent_reasoning[-1])
        self.assertEqual(monitor._recent_reasoning[-1], "Checking for existing technical specs")

    def test_reasoning_panel_lines_wrap_long_entries(self) -> None:
        monitor = self._make_monitor()
        monitor._recent_reasoning.append("Assessing documentation and code structure for event feed improvements and token parsing stability")

        lines = monitor._reasoning_lines_for_panel(max_width=40, max_lines=5)
        self.assertGreater(len(lines), 1)

    def test_event_summary_contains_useful_context(self) -> None:
        monitor = self._make_monitor()
        summary = monitor._summarize_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_name": "ReadFile",
            },
            "",
        )

        self.assertIn("tool_call:started", summary)
        self.assertIn("ReadFile", summary)

    def test_maybe_report_tolerates_live_update_blocking_io(self) -> None:
        class _Live:
            def update(self, *_args, **_kwargs) -> None:
                raise BlockingIOError(35, "write could not complete without blocking")

            def stop(self) -> None:
                return None

        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor.log_path = Path("/tmp/orc.log")
        monitor.metrics = SimpleNamespace(tokens_total=None, total_lines=0, command_count=0, files_edited=None)
        monitor._report_interval = 0.0
        monitor._last_report_time = 0.0
        monitor._last_git_stats_time = 0.0
        monitor._last_ui_render = 0.0
        monitor._spinner_idx = 0
        monitor._live_started = True
        monitor._live_disabled_notified = False
        monitor._plain_status_mode = False
        monitor._last_plain_status_time = 0.0
        monitor._live = _Live()
        monitor._update_git_stats = lambda: None
        monitor._write_metrics_snapshot = lambda: None
        monitor._render = lambda: "render"
        monitor.task_id = "TASK-1"
        monitor._last_event_type = "init"
        monitor._last_event_note = "starting"

        monitor.maybe_report()
        self.assertFalse(monitor._live_started)
        self.assertTrue(monitor._live_disabled_notified)

    def test_maybe_report_does_not_crash_if_warning_output_is_blocked(self) -> None:
        class _Live:
            def update(self, *_args, **_kwargs) -> None:
                raise BlockingIOError(35, "write could not complete without blocking")

            def stop(self) -> None:
                return None

        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor.log_path = Path("/tmp/orc.log")
        monitor.metrics = SimpleNamespace(tokens_total=None, total_lines=0, command_count=0, files_edited=None)
        monitor._report_interval = 0.0
        monitor._last_report_time = 0.0
        monitor._last_git_stats_time = 0.0
        monitor._last_ui_render = 0.0
        monitor._spinner_idx = 0
        monitor._live_started = True
        monitor._live_disabled_notified = False
        monitor._plain_status_mode = False
        monitor._last_plain_status_time = 0.0
        monitor._live = _Live()
        monitor._update_git_stats = lambda: None
        monitor._write_metrics_snapshot = lambda: None
        monitor._render = lambda: "render"
        monitor.task_id = "TASK-1"
        monitor._last_event_type = "init"
        monitor._last_event_note = "starting"

        with patch("orc_core.stream_monitor.ui_warn", side_effect=BlockingIOError(35, "blocked")):
            monitor.maybe_report()

    @patch("orc_core.stream_monitor.os.set_blocking")
    @patch("orc_core.stream_monitor.os.get_blocking", return_value=False)
    def test_ensure_console_output_is_forced_to_blocking(self, get_blocking_mock, set_blocking_mock) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor.log_path = Path("/tmp/orc.log")
        monitor._console = SimpleNamespace(file=SimpleNamespace(fileno=lambda: 1))

        monitor._ensure_console_blocking_output()

        get_blocking_mock.assert_called_once_with(1)
        set_blocking_mock.assert_called_once_with(1, True)

    @patch("orc_core.stream_monitor.os.set_blocking")
    @patch("orc_core.stream_monitor.os.get_blocking", return_value=False)
    def test_ensure_agent_streams_are_forced_to_blocking(self, get_blocking_mock, set_blocking_mock) -> None:
        class _S:
            def __init__(self, fd: int) -> None:
                self._fd = fd

            def fileno(self) -> int:
                return self._fd

        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor.log_path = Path("/tmp/orc.log")
        monitor.proc = SimpleNamespace(stdout=_S(11), stderr=_S(12))

        monitor._ensure_stream_blocking_output()

        self.assertEqual(get_blocking_mock.call_count, 2)
        set_blocking_mock.assert_any_call(11, True)
        set_blocking_mock.assert_any_call(12, True)


if __name__ == "__main__":
    unittest.main()
