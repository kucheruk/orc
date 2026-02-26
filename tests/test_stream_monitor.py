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

    def test_reasoning_chunks_are_coalesced(self) -> None:
        monitor = self._make_monitor()
        event = {"type": "assistant", "subtype": "reasoning"}

        monitor._remember_reasoning(event, "and")
        monitor._remember_reasoning(event, "un")
        monitor._remember_reasoning(event, "tracked")
        monitor._remember_reasoning(event, "files")
        monitor._remember_reasoning(event, "**")

        self.assertEqual(len(monitor._recent_reasoning), 1)
        self.assertIn("untracked", monitor._recent_reasoning[-1])

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
