#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock

from orc_core.infra.monitoring.stream_monitor import StreamJsonMonitor


class StreamMonitorFormattingTest(unittest.TestCase):
    def test_set_progress_tracks_added_delta_and_remaining(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.set_progress(1, 4)
        state.set_progress(2, 6)

        snapshot = state.build_snapshot()
        self.assertEqual(snapshot.progress_done, 2)
        self.assertEqual(snapshot.progress_total, 6)
        self.assertEqual(snapshot.progress_remaining, 4)
        self.assertEqual(snapshot.progress_added_delta, 2)

    def test_snapshot_tracks_last_event_timestamp(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        started_at = time.time() - 10
        state = StreamMonitorState(task_id="TASK-1", started_at=started_at, summary_lines=25)
        initial_snapshot = state.build_snapshot()
        self.assertEqual(initial_snapshot.last_event_at, started_at)

        state.record_event({"type": "assistant", "subtype": "reasoning", "text": "thinking..."})
        updated_snapshot = state.build_snapshot()
        self.assertGreaterEqual(updated_snapshot.last_event_at, initial_snapshot.last_event_at)

    def test_reasoning_delta_and_completed_build_readable_sentence(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "delta", "text": "**Preparing"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " onboarding"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " plan**"})
        state.record_event({"type": "thinking", "subtype": "completed"})

        self.assertEqual(len(state._reasoning._recent_reasoning), 1)
        self.assertEqual(state._reasoning._recent_reasoning[-1], "Preparing onboarding plan")

    def test_reasoning_flushes_buffer_when_completed_missing(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "delta", "text": "Split"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " across"})
        state.record_event({"type": "tool_call", "subtype": "started", "tool_name": "ReadFile"})

        self.assertEqual(state._reasoning._recent_reasoning[-1], "Split across")

    def test_reasoning_update_fragments_preserve_spaces_between_words(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "update", "text": "Понял"})
        state.record_event({"type": "thinking", "subtype": "update", "text": " "})
        state.record_event({"type": "thinking", "subtype": "update", "text": "задачу"})
        state.record_event({"type": "thinking", "subtype": "completed"})

        self.assertIn("Понял задачу", state.reasoning_lines_for_panel()[-1])

    def test_assistant_update_stream_is_collected_into_reasoning(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "Собираю"}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": " plan"}]}})
        state.record_event({"type": "tool_call", "subtype": "started", "tool_name": "ReadFile"})

        self.assertIn("Собираю", state.reasoning_lines_for_panel()[-1])

    def test_assistant_update_preserves_whitespace_only_tokens(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "Понял"}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": " "}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "задачу"}]}})
        state.record_event({"type": "assistant", "subtype": "completed"})

        self.assertIn("Понял задачу", state.reasoning_lines_for_panel()[-1])

    def test_assistant_update_delta_is_hidden_from_event_feed(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": "часть"}]}})
        state.record_event({"type": "assistant", "subtype": "update", "message": {"content": [{"type": "text", "text": " фразы"}]}})

        self.assertEqual(state.build_snapshot().recent_events, [])

    def test_thinking_delta_and_completed_are_hidden_from_event_feed(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "thinking", "subtype": "delta", "text": "**Adding"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " initial"})
        state.record_event({"type": "thinking", "subtype": "delta", "text": " setup**"})
        state.record_event({"type": "thinking", "subtype": "completed"})

        self.assertEqual(state.build_snapshot().recent_events, [])
        self.assertTrue(any("Adding initial setup" in line for line in state.reasoning_lines_for_panel()))

    def test_assistant_message_without_subtype_is_collected_into_reasoning(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "assistant", "message": {"content": [{"type": "text", "text": "Начинаю"}]}})
        state.record_event({"type": "assistant", "message": {"content": [{"type": "text", "text": " работу"}]}})
        state.record_event({"type": "tool_call", "subtype": "started", "tool_name": "ReadFile"})

        self.assertTrue(any("Начинаю" in line for line in state.reasoning_lines_for_panel()))
        self.assertTrue(all(not event.startswith("assistant:") for event in state.build_snapshot().recent_events))

    def test_reasoning_strips_basic_markdown(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        event = {"type": "assistant", "subtype": "reasoning"}
        from orc_core.infra.monitoring.event_text import iter_event_values
        state._reasoning._remember_reasoning(event, "**Checking for existing technical specs**", iter_event_values)

        self.assertEqual(len(state._reasoning._recent_reasoning), 1)
        self.assertNotIn("**", state._reasoning._recent_reasoning[-1])
        self.assertEqual(state._reasoning._recent_reasoning[-1], "Checking for existing technical specs")

    def test_reasoning_panel_lines_wrap_long_entries(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state._reasoning._recent_reasoning.append("Assessing documentation and code structure for event feed improvements and token parsing stability")

        lines = state.reasoning_lines_for_panel(max_width=40, max_lines=5)
        self.assertGreater(len(lines), 1)

    def test_extract_text_reads_message_content_list(self) -> None:
        from orc_core.infra.monitoring.event_text import extract_text

        text = extract_text(
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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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

    def test_incremental_usage_for_same_request_counts_only_growth(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        first = {
            "type": "result",
            "request_id": "req-grow",
            "usage": {"inputTokens": 6, "outputTokens": 4},
        }
        second = {
            "type": "result",
            "request_id": "req-grow",
            "usage": {"inputTokens": 9, "outputTokens": 6},
        }
        state.record_event(first)
        state.record_event(second)

        self.assertEqual(state.metrics.tokens_total, 15)
        self.assertEqual(state.metrics.tokens_source, "structured")

    def test_record_event_accepts_string_token_values_in_structured_usage(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "result",
                "request_id": "req-str",
                "usage": {"inputTokens": "11", "outputTokens": "4"},
            }
        )

        self.assertEqual(state.metrics.tokens_total, 15)
        self.assertEqual(state.metrics.tokens_source, "structured")

    def test_record_event_extracts_tokens_from_raw_when_text_keys_are_nonstandard(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "assistant",
                "payload": {"stats": "usage inputTokens=9 outputTokens=6"},
            }
        )

        self.assertEqual(state.metrics.tokens_total, 15)
        self.assertEqual(state.metrics.tokens_source, "heuristic")

    def test_text_fallback_is_ignored_when_structured_entries_add_zero(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "result",
                "request_id": "req-zero",
                "usage": {"inputTokens": 0, "outputTokens": 0},
                "message": {"content": [{"type": "text", "text": "42 tokens"}]},
            }
        )

        self.assertEqual(state.metrics.tokens_total, 0)
        self.assertEqual(state.metrics.tokens_source, "heuristic")

    def test_text_only_3k_tokens_does_not_set_tokens_total(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Status: ~3k tokens so far"}]},
            }
        )

        self.assertIsNone(state.metrics.tokens_total)
        self.assertEqual(state.metrics.tokens_source, "none")

    def test_event_summary_contains_useful_context(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "result", "subtype": "success", "status": "ok"})
        recent_event = state.build_snapshot().recent_events[-1]

        self.assertRegex(recent_event, r"^\[\d{2}:\d{2}:\d{2}\] ")

    def test_tool_call_with_nested_payload_populates_recent_commands(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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

    def test_tool_call_shell_command_replaces_worktree_prefix_in_recent_commands(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_name": "Shell",
                "arguments": {
                    "command": (
                        "python "
                        "/tmp/fake-project/.orc/worktrees/CORE-005-20260305-110504/scripts/run.py"
                    )
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn("python [worktree]/scripts/run.py", command)
        self.assertNotIn("/.orc/worktrees/", command)

    def test_tool_call_read_replaces_worktree_prefix_in_recent_commands(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "readToolCall": {
                        "args": {
                            "path": "/tmp/fake-project/.orc/worktrees/CORE-005-20260305-110504/src/main.py",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertEqual(command, "read [worktree]/src/main.py")

    def test_tool_call_glob_includes_pattern_and_directory(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "globToolCall": {
                        "args": {
                            "globPattern": "ADR/*.md",
                            "targetDirectory": "/tmp/other-project",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn("glob ADR/*.md", command)
        self.assertIn("/tmp/other-project", command)

    def test_tool_call_glob_replaces_worktree_prefix_in_target_directory(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "globToolCall": {
                        "args": {
                            "globPattern": "**/*.py",
                            "targetDirectory": "/tmp/fake-project/.orc/worktrees/CORE-005-20260305-110504/src",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn("glob **/*.py", command)
        self.assertIn("[worktree]/src", command)
        self.assertNotIn("/.orc/worktrees/", command)

    def test_tool_call_grep_includes_pattern_and_path(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "grepToolCall": {
                        "args": {
                            "pattern": "class\\s+SafeJsonExtensions",
                            "path": "/tmp/other-project/src",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn('grep "class\\s+SafeJsonExtensions"', command)
        self.assertIn("/tmp/other-project/src", command)

    def test_tool_call_grep_replaces_worktree_prefix_in_path(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "grepToolCall": {
                        "args": {
                            "pattern": "main\\(",
                            "path": "/tmp/fake-project/.orc/worktrees/CORE-005-20260305-110504/src",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn('grep "main\\("', command)
        self.assertIn("[worktree]/src", command)
        self.assertNotIn("/.orc/worktrees/", command)

    def test_tool_call_unknown_payload_uses_key_value_fallback(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

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

    def test_tool_call_unknown_payload_replaces_worktree_prefix_in_fallback_values(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "customToolCall": {
                        "args": {
                            "path": "/tmp/fake-project/.orc/worktrees/CORE-005-20260305-110504/file.txt",
                        }
                    }
                },
            }
        )

        command = state.build_snapshot().recent_commands[-1]
        self.assertIn("custom path=[worktree]/file.txt", command)
        self.assertNotIn("/.orc/worktrees/", command)

    def test_recent_files_replaces_worktree_prefix(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "readToolCall": {
                        "args": {
                            "path": "/tmp/fake-project/.orc/worktrees/CORE-005-20260305-110504/src/module.py",
                        }
                    }
                },
            }
        )

        recent_file = state.build_snapshot().recent_files[-1]
        self.assertEqual(recent_file, "[worktree]/src/module.py")

    def test_recent_files_keeps_non_worktree_path_unchanged(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "tool_call": {
                    "readToolCall": {
                        "args": {
                            "path": "/tmp/orc-repo/README.md",
                        }
                    }
                },
            }
        )

        recent_file = state.build_snapshot().recent_files[-1]
        self.assertEqual(recent_file, "/tmp/orc-repo/README.md")

    def test_live_status_switches_to_tool_call_when_tool_starts(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-1",
                "tool_call": {"readToolCall": {"args": {"path": "/tmp/demo.txt"}}},
            }
        )
        snapshot = state.build_snapshot()
        self.assertEqual(snapshot.live_phase, "tool_call")
        self.assertIn("running read /tmp/demo.txt", snapshot.live_status.lower())
        self.assertEqual(snapshot.active_tool_call_count, 1)
        self.assertFalse(snapshot.is_subagent_activity)

    def test_live_status_marks_subagent_phase_for_task_tool(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-task",
                "tool_call": {"taskToolCall": {"args": {"description": "run subagent"}}},
            }
        )
        snapshot = state.build_snapshot()
        self.assertEqual(snapshot.live_phase, "subagent")
        self.assertTrue(snapshot.is_subagent_activity)
        self.assertEqual(snapshot.active_tool_call_count, 1)

    def test_live_status_returns_to_waiting_after_tool_completion(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-2",
                "tool_call": {"globToolCall": {"args": {"globPattern": "**/*.py"}}},
            }
        )
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "completed",
                "call_id": "call-2",
            }
        )
        snapshot = state.build_snapshot()
        self.assertEqual(snapshot.live_phase, "waiting")
        self.assertEqual(snapshot.active_tool_call_count, 0)

    def test_live_status_shows_network_problem_during_reconnect_and_retry(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event({"type": "connection", "subtype": "reconnecting"})
        reconnect_snapshot = state.build_snapshot()
        self.assertEqual(reconnect_snapshot.live_phase, "network_problem")
        self.assertIn("network problems", reconnect_snapshot.live_status.lower())

        state.record_event({"type": "retry", "subtype": "starting", "attempt": 3, "is_resume": True})
        retry_snapshot = state.build_snapshot()
        self.assertEqual(retry_snapshot.live_phase, "network_problem")
        self.assertIn("attempt 3", retry_snapshot.live_status.lower())

        state.record_event({"type": "connection", "subtype": "reconnected"})
        recovered_snapshot = state.build_snapshot()
        self.assertEqual(recovered_snapshot.live_phase, "waiting")
        self.assertIn("recovered", recovered_snapshot.live_status.lower())

    def test_force_finalize_live_tool_calls_clears_stuck_tool_phase(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-stuck",
                "tool_call": {
                    "shellToolCall": {"args": {"command": "./scripts/ci/lint.sh && dotnet build -c Release Bobot.sln"}}
                },
            }
        )
        result = state.force_finalize_live_tool_calls("process_exited")
        snapshot = state.build_snapshot()

        self.assertEqual(result.get("cleared"), 1)
        self.assertEqual(snapshot.live_phase, "waiting")
        self.assertEqual(snapshot.active_tool_call_count, 0)
        self.assertIn("forced tool close", snapshot.live_status)

    def test_active_tool_calls_watchdog_snapshot_reports_oldest_active_call(self) -> None:
        from orc_core.infra.monitoring.stream_monitor_state import StreamMonitorState

        state = StreamMonitorState(task_id="TASK-1", started_at=time.time(), summary_lines=25)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-one",
                "tool_call": {"readToolCall": {"args": {"path": "/tmp/a.txt"}}},
            }
        )
        time.sleep(0.01)
        state.record_event(
            {
                "type": "tool_call",
                "subtype": "started",
                "call_id": "call-two",
                "tool_call": {"shellToolCall": {"args": {"command": "echo hi"}}},
            }
        )

        snapshot = state.active_tool_calls_watchdog_snapshot()
        self.assertEqual(snapshot.get("count"), 2)
        self.assertGreater(float(snapshot.get("oldest_age_seconds") or 0.0), 0.0)
        self.assertIn(str(snapshot.get("oldest_label") or ""), {"read /tmp/a.txt", "echo hi"})

    def test_refresh_process_status_syncs_proxy_returncode(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        agent = SimpleNamespace(
            proc=SimpleNamespace(returncode=None),
            _proc=SimpleNamespace(returncode=7),
        )
        def _refresh() -> int | None:
            rc = agent._proc.returncode
            if rc is not None:
                agent.proc.returncode = rc
            return agent.proc.returncode
        agent.refresh_status = _refresh
        monitor._agent = agent
        monitor.proc = agent.proc

        value = monitor.refresh_process_status()

        self.assertEqual(value, 7)
        self.assertEqual(monitor.proc.returncode, 7)

    def test_refresh_backlog_progress_reads_counts_from_backlog_file(self) -> None:
        from orc_core.infra.monitoring.monitor_metrics_collector import MonitorMetricsCollector
        from orc_core.tasks.task_source import MarkdownTaskSource
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backlog_path = root / "BACKLOG.md"
            backlog_path.write_text("- [x] TASK-001 done\n- [ ] TASK-002 open\n- [ ] TASK-003 open\n", encoding="utf-8")
            state = MagicMock()
            state._progress_in_progress = 0
            collector = MonitorMetricsCollector(
                task_id="TASK-001", workdir=str(root), log_path=root / ".orc" / "orc.log",
                metrics=MagicMock(), task_state_path=root / ".cursor" / "orc-task.json",
                task_runtime_state_path=root / "runtime.json", stats_path=root / "stats.json",
                metrics_path=root / "metrics.json", timeline_id="", attempt=0, started_at=0.0,
                backlog_task_lister=lambda p: MarkdownTaskSource(p).list_tasks(),
            )
            collector.refresh_backlog_progress(state)

        args = state.set_progress.call_args[0]
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1], 3)

    def test_append_agent_output_writes_to_log_file(self) -> None:
        from orc_core.infra.monitoring.agent_output_sink import AgentOutputSink
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "agent-output.log"
            log_path = Path(tmpdir) / "orc.log"
            sink = AgentOutputSink(str(output_path), task_id="T-1", log_path=log_path)
            sink.append("stdout", '{"type":"result"}\n')
            sink.append("stderr", "warning")
            sink.close()
            content = output_path.read_text(encoding="utf-8")

        self.assertIn('[stdout] {"type":"result"}', content)
        self.assertIn("[stderr] warning", content)

    def test_followup_detection_uses_result_error_context(self) -> None:
        from orc_core.infra.monitoring.stream_parser import is_followup_prompt_event
        detected = is_followup_prompt_event(
            "result",
            "error",
            '{"type":"result","subtype":"error","text":"Please add a follow-up question"}',
        )
        self.assertTrue(detected)

    def test_followup_detection_ignores_non_error_results(self) -> None:
        from orc_core.infra.monitoring.stream_parser import is_followup_prompt_event
        detected = is_followup_prompt_event(
            "result",
            "success",
            '{"type":"result","subtype":"success","text":"add a follow-up"}',
        )
        self.assertFalse(detected)

    def test_runtime_heartbeat_updates_runtime_file_only(self) -> None:
        from orc_core.infra.monitoring.monitor_metrics_collector import MonitorMetricsCollector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_path = root / ".cursor" / "orc-task.json"
            runtime_path = root / ".cursor" / "orc-task-runtime.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps({"task_id": "TASK-001", "conversation_id": "conv-123"}, ensure_ascii=False),
                encoding="utf-8",
            )
            runtime_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "task_id": "TASK-001",
                        "active_seconds": 3.0,
                        "last_heartbeat_at": time.time() - 5.0,
                        "run_id": "run-1",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            collector = MonitorMetricsCollector(
                task_id="TASK-001", workdir=str(root), log_path=root / ".orc" / "orc.log",
                metrics=MagicMock(), task_state_path=task_path,
                task_runtime_state_path=runtime_path, stats_path=root / "stats.json",
                metrics_path=root / "metrics.json", timeline_id="", attempt=0, started_at=0.0,
            )
            # Override run_id to match the fixture
            collector._run_id = "run-1"
            collector.update_task_runtime_state()

            task_payload = json.loads(task_path.read_text(encoding="utf-8"))
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        self.assertEqual(task_payload.get("conversation_id"), "conv-123")
        self.assertGreater(runtime_payload.get("active_seconds", 0.0), 3.0)
        self.assertEqual(runtime_payload.get("run_id"), "run-1")

    def test_runtime_heartbeat_does_not_overwrite_task_conversation_state(self) -> None:
        from orc_core.infra.monitoring.monitor_metrics_collector import MonitorMetricsCollector
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_path = root / ".cursor" / "orc-task.json"
            runtime_path = root / ".cursor" / "orc-task-runtime.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps({"task_id": "TASK-001", "conversation_id": ""}, ensure_ascii=False),
                encoding="utf-8",
            )
            runtime_path.write_text(
                json.dumps(
                    {"version": 1, "task_id": "TASK-001", "active_seconds": 0.0, "last_heartbeat_at": 0.0, "run_id": ""},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            task_payload = json.loads(task_path.read_text(encoding="utf-8"))
            task_payload["conversation_id"] = "conv-123"
            task_path.write_text(json.dumps(task_payload, ensure_ascii=False), encoding="utf-8")
            collector = MonitorMetricsCollector(
                task_id="TASK-001", workdir=str(root), log_path=root / ".orc" / "orc.log",
                metrics=MagicMock(), task_state_path=task_path,
                task_runtime_state_path=runtime_path, stats_path=root / "stats.json",
                metrics_path=root / "metrics.json", timeline_id="", attempt=0, started_at=0.0,
            )
            collector._run_id = "run-1"
            collector.update_task_runtime_state()

            final_task_payload = json.loads(task_path.read_text(encoding="utf-8"))
        self.assertEqual(final_task_payload.get("conversation_id"), "conv-123")


if __name__ == "__main__":
    unittest.main()
