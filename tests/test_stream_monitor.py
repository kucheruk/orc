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

    def test_reasoning_delta_and_completed_build_readable_sentence(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "delta", "text": "**Preparing"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " onboarding"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " plan**"})
        state.record_event({"type": "thinking", "subtype": "completed"})

        self.assertEqual(len(state._recent_reasoning), 1)
        self.assertEqual(state._recent_reasoning[-1], "Preparing onboarding plan")

    def test_reasoning_flushes_buffer_when_completed_missing(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "delta", "text": "Split"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " across"})
        state.record_event({"type": "tool_call", "subtype": "started", "tool_name": "ReadFile"})

        self.assertEqual(state._recent_reasoning[-1], "Split across")

    def test_reasoning_update_fragments_preserve_spaces_between_words(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "update", "text": "Понял"})
        state.record_event({"type": "thinking", "subtype": "update", "text": " "})
        state.record_event({"type": "thinking", "subtype": "update", "text": "задачу"})
        state.record_event({"type": "thinking", "subtype": "completed"})

        self.assertIn("Понял задачу", state.reasoning_lines_for_panel()[-1])

    def test_assistant_update_stream_is_collected_into_reasoning(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "Собираю"}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": " plan"}]}})
        state.record_event({"type": "tool_call", "subtype": "started", "tool_name": "ReadFile"})

        self.assertIn("Собираю", state.reasoning_lines_for_panel()[-1])

    def test_assistant_update_preserves_whitespace_only_tokens(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "Понял"}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": " "}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "задачу"}]}})
        state.record_event({"type": "assistant", "subtype": "completed"})

        self.assertIn("Понял задачу", state.reasoning_lines_for_panel()[-1])

    def test_assistant_update_delta_is_hidden_from_event_feed(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "часть"}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": " фразы"}]}})

        self.assertEqual(state.build_snapshot().recent_events, [])

    def test_thinking_delta_and_completed_are_hidden_from_event_feed(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "delta", "text": "**Adding"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " initial"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " setup**"})
        state.record_event({"type": "thinking", "subtype": "completed"})

        self.assertEqual(state.build_snapshot().recent_events, [])
        self.assertTrue(any("Adding initial setup" in line for line in state.reasoning_lines_for_panel()))

    def test_assistant_message_without_subtype_is_collected_into_reasoning(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "message": {"content": [{"type": "text", "text": "Начинаю"}]}})
        state.record_event({"type": "assistant", "message": {"content": [{"type": "text", "text": " работу"}]}})
        state.record_event({"type": "tool_call", "subtype": "started", "tool_name": "ReadFile"})

        self.assertTrue(any("Начинаю" in line for line in state.reasoning_lines_for_panel()))
        self.assertTrue(all(not event.startswith("assistant:") for event in state.build_snapshot().recent_events))

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

    def test_extract_text_reads_message_content_list(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        text = state._extract_text(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Inspecting README"},
                        {"type": "text", "text": "and ADR"},
                    ]
                },
            }
        )
        self.assertIn("Inspecting README", text)
        self.assertIn("and ADR", text)

    def test_record_event_sums_structured_token_usage_once_per_request(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event = {
            "type": "result",
            "request_id": "req-1",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        state.record_event(event)
        state.record_event(event)

        self.assertEqual(state.metrics.tokens_total, 15)
        self.assertEqual(state.metrics.tokens_status, "known")
        self.assertEqual(state.metrics.tokens_source, "structured")

    def test_record_event_sums_camel_case_usage_from_result_event(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event = {
            "type": "result",
            "request_id": "req-2",
            "usage": {"inputTokens": 10, "outputTokens": 7, "cacheReadTokens": 100},
        }
        state.record_event(event)

        self.assertEqual(state.metrics.tokens_total, 17)
        self.assertEqual(state.metrics.tokens_status, "known")
        self.assertEqual(state.metrics.tokens_source, "structured")

    def test_duplicate_camel_case_usage_is_deduplicated_per_request(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event = {
            "type": "result",
            "request_id": "req-dup",
            "usage": {"inputTokens": 3, "outputTokens": 2},
        }
        state.record_event(event)
        state.record_event(event)

        self.assertEqual(state.metrics.tokens_total, 5)
        self.assertEqual(state.metrics.tokens_source, "structured")

    def test_structured_usage_takes_precedence_over_text_token_fallback(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event = {
            "type": "result",
            "request_id": "req-3",
            "usage": {"inputTokens": 8, "outputTokens": 4},
            "message": {"content": [{"type": "text", "text": "2000 tokens"}]},
        }
        state.record_event(event)

        self.assertEqual(state.metrics.tokens_total, 12)
        self.assertEqual(state.metrics.tokens_source, "structured")

    def test_same_usage_payload_counts_for_different_request_ids(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event_one = {
            "type": "result",
            "request_id": "req-A",
            "usage": {"inputTokens": 5, "outputTokens": 5},
        }
        event_two = {
            "type": "result",
            "request_id": "req-B",
            "usage": {"inputTokens": 5, "outputTokens": 5},
        }
        state.record_event(event_one)
        state.record_event(event_two)

        self.assertEqual(state.metrics.tokens_total, 20)

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

    def test_event_summary_has_simple_timestamp_prefix(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "result", "subtype": "success", "status": "ok"})
        recent_event = state.build_snapshot().recent_events[-1]

        self.assertRegex(recent_event, r"^\[\d{2}:\d{2}:\d{2}\] ")

    def test_tool_call_with_nested_payload_populates_recent_commands(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "readToolCall": {
                        "args": {"path": "/tmp/a.txt"},
                    }
                },
            }
        )

        snapshot = state.build_snapshot()
        self.assertIn("read /tmp/a.txt", [cmd.lower() for cmd in snapshot.recent_commands])

    def test_tool_call_prefers_shell_command_with_arguments_for_recent_commands(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_name": "Shell",
                "arguments": {"command": "git status --short"},
            }
        )

        snapshot = state.build_snapshot()
        self.assertIn("git status --short", snapshot.recent_commands)

    def test_tool_call_glob_includes_pattern_and_directory(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "globToolCall": {
                        "args": {
                            "globPattern": "ADR/*.md",
                            "targetDirectory": "/Users/vetinary/work/nadmozg",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn("glob ADR/*.md", command)
        self.assertIn("/Users/vetinary/work/nadmozg", command)

    def test_tool_call_grep_includes_pattern_and_path(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "grepToolCall": {
                        "args": {
                            "pattern": "class\\s+SafeJsonExtensions",
                            "path": "/Users/vetinary/work/nadmozg/src",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn('grep "class\\s+SafeJsonExtensions"', command)
        self.assertIn("/Users/vetinary/work/nadmozg/src", command)

    def test_tool_call_unknown_payload_uses_key_value_fallback(self) -> None:
        from orc_core.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "customToolCall": {
                        "args": {
                            "foo": "bar",
                            "n": 7,
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn("custom foo=bar", command)
        self.assertIn("n=7", command)

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
