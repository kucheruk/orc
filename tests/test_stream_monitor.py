#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock

from orc_core.stream_monitor import StreamJsonMonitor


class StreamMonitorFormattingTest(unittest.TestCase):
    def test_snapshot_tracks_last_event_timestamp(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        started_at = time.time() - 10
        state = StreamMonitorState(task_id="TASK-1", started_at=started_at, summary_lines=25)
        initial_snapshot = state.build_snapshot()
        self.assertEqual(initial_snapshot.last_event_at, started_at)

        state.record_event({"type": "assistant", "subtype": "reasoning", "text": "thinking..."})
        updated_snapshot = state.build_snapshot()
        self.assertGreaterEqual(updated_snapshot.last_event_at, initial_snapshot.last_event_at)

    def test_reasoning_chunks_are_coalesced_without_word_split(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.append_reasoning_fragment("Prior")
        state.append_reasoning_fragment("itizing user commit preference")

        self.assertEqual(len(state._recent_reasoning), 1)
        self.assertEqual(state._recent_reasoning[-1], "Prioritizing user commit preference")

    def test_reasoning_chunks_keep_spaces_between_words(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.append_reasoning_fragment("Acknowledging")
        state.append_reasoning_fragment("task DB-005 and preparing initial steps")

        self.assertEqual(state._recent_reasoning[-1], "Acknowledging task DB-005 and preparing initial steps")

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
        monitor._update_git_stats = lambda: None
        monitor._write_metrics_snapshot = lambda: None
        monitor._publish_snapshot = MagicMock()
        monitor.task_id = "TASK-1"

        monitor.maybe_report()
        monitor._state.tick_spinner.assert_called_once()
        monitor._publish_snapshot.assert_called_once()

    def test_append_agent_output_writes_to_log_file(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "agent-output.log"
            monitor._agent_output_file = output_path.open("a", encoding="utf-8")
            monitor._append_agent_output("stdout", '{"type":"result"}\n')
            monitor._append_agent_output("stderr", "warning")
            monitor._agent_output_file.close()
            content = output_path.read_text(encoding="utf-8")

        self.assertIn('[stdout] {"type":"result"}', content)
        self.assertIn("[stderr] warning", content)

    def test_followup_detection_uses_result_error_context(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        detected = monitor._is_followup_prompt_event(
            "result",
            "error",
            '{"type":"result","subtype":"error","text":"Please add a follow-up question"}',
        )
        self.assertTrue(detected)

    def test_followup_detection_ignores_non_error_results(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        detected = monitor._is_followup_prompt_event(
            "result",
            "success",
            '{"type":"result","subtype":"success","text":"add a follow-up"}',
        )
        self.assertFalse(detected)

    def test_publish_snapshot_uses_injected_callback(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor._state = MagicMock()
        snapshot = object()
        monitor._state.build_snapshot.return_value = snapshot
        monitor._snapshot_publisher = MagicMock()

        monitor._publish_snapshot()

        monitor._snapshot_publisher.assert_called_once_with(snapshot)

    def test_stop_skips_threadsafe_wakeup_when_loop_closed(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor._stop = MagicMock()
        monitor._runner_thread = MagicMock()
        monitor._runner_thread.is_alive.return_value = False
        monitor._agent_output_file = None
        monitor._loop = MagicMock()
        monitor._loop.is_closed.return_value = True

        monitor.stop()

        monitor._stop.set.assert_called_once()
        monitor._loop.call_soon_threadsafe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
