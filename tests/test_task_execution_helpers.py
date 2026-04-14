#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for standalone helper functions extracted from task_execution."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from orc_core.tasks.task_execution_helpers import (
    _find_first_stage_index,
    _is_fragmented_summary_lines,
    _normalize_fragmented_summary_text,
    _resolve_runtime_backlog_path,
    _restart_backoff_seconds,
    _should_defer_base_backlog_sync_to_integration,
)
from orc_core.tasks.execution.stage import TaskStageSpec


class RestartBackoffTest(unittest.TestCase):
    def test_first_restart_is_one_second(self):
        self.assertEqual(_restart_backoff_seconds(0), 1.0)

    def test_second_restart_is_one_second(self):
        self.assertEqual(_restart_backoff_seconds(1), 1.0)

    def test_third_restart_is_two_seconds(self):
        self.assertEqual(_restart_backoff_seconds(2), 2.0)

    def test_capped_at_30(self):
        self.assertEqual(_restart_backoff_seconds(10), 30.0)
        self.assertEqual(_restart_backoff_seconds(100), 30.0)


class FragmentedSummaryTest(unittest.TestCase):
    def test_short_list_not_fragmented(self):
        self.assertFalse(_is_fragmented_summary_lines(["a", "b"]))

    def test_long_lines_not_fragmented(self):
        lines = ["This is a long line" for _ in range(10)]
        self.assertFalse(_is_fragmented_summary_lines(lines))

    def test_many_short_lines_is_fragmented(self):
        lines = ["word"] * 10
        self.assertTrue(_is_fragmented_summary_lines(lines))

    def test_normalize_joins_fragments(self):
        text = "Hello\nworld\n,\nhow\nare\nyou\n?"
        result = _normalize_fragmented_summary_text(text)
        self.assertIn("Hello", result)
        self.assertNotIn("\n", result)

    def test_normalize_empty(self):
        self.assertEqual(_normalize_fragmented_summary_text(""), "")

    def test_normalize_non_fragmented_preserves_newlines(self):
        text = "This is a long first line\nThis is a long second line\nThis is a long third line"
        result = _normalize_fragmented_summary_text(text)
        self.assertIn("\n", result)


class ResolveRuntimeBacklogPathTest(unittest.TestCase):
    def test_empty_arg_returns_backlog_path(self):
        request = MagicMock()
        request.backlog_arg = ""
        request.backlog_path = Path("/base/backlog.md")
        self.assertEqual(_resolve_runtime_backlog_path(request), Path("/base/backlog.md"))

    def test_absolute_arg_returned_as_is(self):
        request = MagicMock()
        request.backlog_arg = "/abs/path.md"
        request.backlog_path = Path("/base/backlog.md")
        self.assertEqual(_resolve_runtime_backlog_path(request), Path("/abs/path.md"))

    def test_relative_arg_joined_with_workdir(self):
        request = MagicMock()
        request.backlog_arg = "relative/backlog.md"
        request.backlog_path = Path("/base/backlog.md")
        request.workdir = "/work"
        self.assertEqual(_resolve_runtime_backlog_path(request), Path("/work/relative/backlog.md"))


class FindFirstStageIndexTest(unittest.TestCase):
    def test_finds_matching_stage(self):
        specs = [TaskStageSpec("impl", "m1", "t1"), TaskStageSpec("review", "m2", "t2")]
        self.assertEqual(_find_first_stage_index(specs, "review"), 1)

    def test_case_insensitive(self):
        specs = [TaskStageSpec("Impl", "m1", "t1")]
        self.assertEqual(_find_first_stage_index(specs, "impl"), 0)

    def test_returns_none_if_not_found(self):
        specs = [TaskStageSpec("impl", "m1", "t1")]
        self.assertIsNone(_find_first_stage_index(specs, "missing"))


class DeferBacklogSyncTest(unittest.TestCase):
    def test_no_defer_when_not_integrating(self):
        self.assertFalse(_should_defer_base_backlog_sync_to_integration(
            integrate_to_main=False,
            base_backlog_path=Path("/a"),
            runtime_backlog_path=Path("/b"),
        ))

    def test_no_defer_when_same_path(self):
        self.assertFalse(_should_defer_base_backlog_sync_to_integration(
            integrate_to_main=True,
            base_backlog_path=Path("/a"),
            runtime_backlog_path=Path("/a"),
        ))

    def test_defer_when_integrating_with_different_paths(self):
        self.assertTrue(_should_defer_base_backlog_sync_to_integration(
            integrate_to_main=True,
            base_backlog_path=Path("/a"),
            runtime_backlog_path=Path("/b"),
        ))


if __name__ == "__main__":
    unittest.main()
