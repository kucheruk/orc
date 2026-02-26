#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import deque
import unittest

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


if __name__ == "__main__":
    unittest.main()
