#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orc_core.runner import launch_agent_stream_json


class RunnerLaunchTest(unittest.TestCase):
    @patch("orc_core.runner.StreamJsonMonitor")
    def test_resume_latest_uses_continue_flag(self, monitor_cls_mock) -> None:
        monitor_instance = MagicMock()
        monitor_cls_mock.return_value = monitor_instance

        launch_agent_stream_json(
            workdir=".",
            prompt_path=None,
            model="gpt-5.3-codex",
            log_path=Path("/tmp/orc.log"),
            report_interval=2.0,
            summary_lines=25,
            task_id="TASK-1",
            progress_done=1,
            progress_total=2,
            resume_latest=True,
            resume_prompt="continue",
        )

        cmd = monitor_cls_mock.call_args.kwargs["agent_cmd"]
        self.assertIn("--continue", cmd)
        self.assertNotIn("--resume", cmd)
        self.assertEqual(cmd[-1], "continue")
        monitor_instance.set_progress.assert_called_once_with(1, 2)

    @patch("orc_core.runner.StreamJsonMonitor")
    def test_resume_id_keeps_resume_flag(self, monitor_cls_mock) -> None:
        monitor_instance = MagicMock()
        monitor_cls_mock.return_value = monitor_instance

        launch_agent_stream_json(
            workdir=".",
            prompt_path=None,
            model="gpt-5.3-codex",
            log_path=Path("/tmp/orc.log"),
            report_interval=2.0,
            summary_lines=25,
            task_id="TASK-1",
            resume_id="chat-123",
            resume_prompt="continue",
        )

        cmd = monitor_cls_mock.call_args.kwargs["agent_cmd"]
        self.assertIn("--resume", cmd)
        self.assertIn("chat-123", cmd)
        self.assertEqual(cmd[-1], "continue")


if __name__ == "__main__":
    unittest.main()
