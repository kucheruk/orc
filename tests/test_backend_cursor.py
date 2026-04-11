#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.cli.agent_preflight import AgentNotInstalledError
from orc_core.backends.cursor import CursorBackend


class CursorBuildCmdTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = CursorBackend()

    def test_fresh_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="gpt-5.3-codex", prompt="do something")
        self.assertEqual(cmd, [
            "agent", "-p", "--force",
            "--model", "gpt-5.3-codex",
            "--output-format", "stream-json",
            "--stream-partial-output",
            "do something",
        ])

    def test_resume_by_id(self) -> None:
        cmd = self.backend.build_agent_cmd(model="gpt-5.3-codex", resume_id="abc-123")
        self.assertIn("--resume", cmd)
        self.assertIn("abc-123", cmd)
        self.assertNotIn("--continue", cmd)

    def test_resume_by_id_with_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="gpt-5.3-codex", resume_id="abc-123", resume_prompt="keep going")
        idx = cmd.index("abc-123")
        self.assertEqual(cmd[idx + 1], "keep going")

    def test_resume_latest(self) -> None:
        cmd = self.backend.build_agent_cmd(model="gpt-5.3-codex", resume_latest=True)
        self.assertIn("--continue", cmd)
        self.assertNotIn("--resume", cmd)

    def test_resume_latest_with_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="gpt-5.3-codex", resume_latest=True, resume_prompt="next task")
        idx = cmd.index("--continue")
        self.assertEqual(cmd[idx + 1], "next task")

    def test_no_prompt_no_resume_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.backend.build_agent_cmd(model="gpt-5.3-codex")

    def test_output_format_is_stream_json(self) -> None:
        cmd = self.backend.build_agent_cmd(model="m", prompt="p")
        idx = cmd.index("--output-format")
        self.assertEqual(cmd[idx + 1], "stream-json")


class CursorPreflightTest(unittest.TestCase):
    @patch("shutil.which", return_value=None)
    def test_not_installed_raises(self, _mock_which) -> None:
        with self.assertRaises(AgentNotInstalledError):
            CursorBackend().ensure_installed()

    @patch("shutil.which", return_value="/usr/local/bin/agent")
    def test_installed_ok(self, _mock_which) -> None:
        CursorBackend().ensure_installed()


class CursorHooksTest(unittest.TestCase):
    def test_setup_hooks_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            log_path.touch()
            CursorBackend().setup_hooks(tmpdir, log_path)
            self.assertTrue((Path(tmpdir) / ".cursor" / "hooks" / "orc_stop.py").exists())
            self.assertTrue((Path(tmpdir) / ".cursor" / "hooks.json").exists())


class CursorDefaultModelTest(unittest.TestCase):
    def test_default_model(self) -> None:
        self.assertEqual(CursorBackend().default_model(), "gpt-5.3-codex")


if __name__ == "__main__":
    unittest.main()
