#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.backends.claude import ClaudeBackend, ClaudeNotInstalledError


class ClaudeBuildCmdTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = ClaudeBackend()

    def test_fresh_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="sonnet", prompt="do something")
        self.assertEqual(cmd[0], "claude")
        self.assertIn("-p", cmd)
        self.assertIn("--output-format", cmd)
        self.assertIn("stream-json", cmd)
        self.assertIn("--verbose", cmd)
        self.assertIn("--dangerously-skip-permissions", cmd)
        self.assertIn("--model", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet")
        self.assertEqual(cmd[-1], "do something")

    def test_resume_by_session_id(self) -> None:
        cmd = self.backend.build_agent_cmd(model="sonnet", resume_id="uuid-123")
        self.assertIn("-r", cmd)
        self.assertIn("uuid-123", cmd)

    def test_resume_by_id_with_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="sonnet", resume_id="uuid-123", resume_prompt="keep going")
        idx = cmd.index("uuid-123")
        self.assertEqual(cmd[idx + 1], "keep going")

    def test_resume_latest(self) -> None:
        cmd = self.backend.build_agent_cmd(model="sonnet", resume_latest=True)
        self.assertIn("--continue", cmd)

    def test_no_prompt_no_resume_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.backend.build_agent_cmd(model="sonnet")

    def test_no_force_flag(self) -> None:
        cmd = self.backend.build_agent_cmd(model="sonnet", prompt="p")
        self.assertNotIn("--force", cmd)

    def test_no_stream_partial_output(self) -> None:
        cmd = self.backend.build_agent_cmd(model="sonnet", prompt="p")
        self.assertNotIn("--stream-partial-output", cmd)


class ClaudePreflightTest(unittest.TestCase):
    @patch("shutil.which", return_value=None)
    def test_not_installed_raises(self, _mock_which) -> None:
        with self.assertRaises(ClaudeNotInstalledError):
            ClaudeBackend().ensure_installed()

    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_installed_ok(self, _mock_which) -> None:
        ClaudeBackend().ensure_installed()


class ClaudeResumeTest(unittest.TestCase):
    def test_get_resume_id_returns_none(self) -> None:
        self.assertIsNone(ClaudeBackend().get_resume_id(".", Path("/tmp/log")))


class ClaudeDefaultModelTest(unittest.TestCase):
    def test_default_model(self) -> None:
        self.assertEqual(ClaudeBackend().default_model(), "sonnet")


if __name__ == "__main__":
    unittest.main()
