#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import unittest

from orc_core.execution_screen import PromptToolkitExecutionScreen
from orc_core.stream_monitor_state import MetricsStore, MonitorSnapshot


class ExecutionScreenRenderTest(unittest.TestCase):
    def test_render_text_contains_key_sections(self) -> None:
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
        )
        screen = PromptToolkitExecutionScreen(lambda: snapshot, refresh_interval=0.2)

        text = screen._render_text(snapshot)

        self.assertIn("Task: TASK-1", text)
        self.assertIn("Recent Commands | Files", text)
        self.assertIn("Reasoning (latest)", text)
        self.assertIn("Event Feed", text)


if __name__ == "__main__":
    unittest.main()
