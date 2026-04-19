#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.backends.codex import CodexBackend, CodexNotInstalledError


class CodexBuildCmdTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = CodexBackend()

    def test_fresh_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="codex-mini", prompt="do something")
        self.assertEqual(cmd, [
            "codex", "exec", "--full-auto",
            "--model", "codex-mini",
            "--json",
            "do something",
        ])

    def test_resume_uses_last(self) -> None:
        cmd = self.backend.build_agent_cmd(model="codex-mini", resume_latest=True)
        self.assertEqual(cmd[:4], ["codex", "exec", "resume", "--last"])

    def test_resume_by_id(self) -> None:
        cmd = self.backend.build_agent_cmd(model="codex-mini", resume_id="some-id")
        self.assertEqual(cmd, ["codex", "exec", "resume", "some-id"])

    def test_resume_with_prompt(self) -> None:
        cmd = self.backend.build_agent_cmd(model="codex-mini", resume_latest=True, resume_prompt="keep going")
        self.assertEqual(cmd[-1], "keep going")

    def test_no_prompt_no_resume_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.backend.build_agent_cmd(model="codex-mini")

    def test_json_flag_present(self) -> None:
        cmd = self.backend.build_agent_cmd(model="m", prompt="p")
        self.assertIn("--json", cmd)

    def test_full_auto_present(self) -> None:
        cmd = self.backend.build_agent_cmd(model="m", prompt="p")
        self.assertIn("--full-auto", cmd)


class CodexPreflightTest(unittest.TestCase):
    @patch("shutil.which", return_value=None)
    def test_not_installed_raises(self, _mock_which) -> None:
        with self.assertRaises(CodexNotInstalledError):
            CodexBackend().ensure_installed()

    @patch("shutil.which", return_value="/usr/local/bin/codex")
    def test_installed_ok(self, _mock_which) -> None:
        CodexBackend().ensure_installed()


class CodexResumeTest(unittest.TestCase):
    def test_get_resume_id_returns_none(self) -> None:
        self.assertIsNone(CodexBackend().get_resume_id(".", Path("/tmp/log")))


class CodexDefaultModelTest(unittest.TestCase):
    def test_default_model(self) -> None:
        self.assertEqual(CodexBackend().default_model(), "codex-mini")


if __name__ == "__main__":
    unittest.main()
