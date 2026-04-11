#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import json
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core.cli import cli_app
from orc_core.cli.cli_app import _failure_message


class CliAppParserTest(unittest.TestCase):
    def test_parser_debug_help_mentions_system_temp_directory(self) -> None:
        parser = cli_app.build_parser()
        debug_action = next((action for action in parser._actions if "--debug" in action.option_strings), None)
        self.assertIsNotNone(debug_action)
        self.assertIn("system temp directory", str(debug_action.help))

    def test_parser_supports_agent_output_log_flag(self) -> None:
        parsed = cli_app.build_parser().parse_args(["--agent-output-log"])
        self.assertTrue(parsed.agent_output_log)

    def test_parser_defaults(self) -> None:
        parsed = cli_app.build_parser().parse_args([])
        self.assertEqual(parsed.backend, "cursor")
        self.assertEqual(parsed.workspace, ".")
        self.assertEqual(parsed.max_sessions, 0)
        self.assertTrue(parsed.commit_phase)


class CliAppFailureMessageTest(unittest.TestCase):
    def test_model_unavailable_suggests_listing_models(self) -> None:
        message = _failure_message("model_unavailable")
        self.assertIn("agent --list-models", message)
        self.assertIn("--model", message)

    def test_dirty_base_repo_failure_includes_paths_and_next_step(self) -> None:
        message = _failure_message("main_integration_preflight_failed:dirty_base_repo:tracked:BACKLOG.md")
        self.assertIn("BACKLOG.md", message)
        self.assertIn("git status --porcelain", message)

    def test_unknown_failure_reason_is_included(self) -> None:
        message = _failure_message("custom_reason")
        self.assertIn("custom_reason", message)


class CliAppCrashDiagnosticsTest(unittest.TestCase):
    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("orc_core.cli.cli_app.ui_error")
    @patch("orc_core.cli.cli_app.build_parser")
    @patch("orc_core.cli.cli_app.ensure_agent_installed", side_effect=RuntimeError("boom"))
    def test_main_emits_crash_json_to_stdout_on_unhandled_exception(
        self,
        _ensure_agent_installed_mock,
        build_parser_mock,
        _ui_error_mock,
        stdout_mock: io.StringIO,
        stderr_mock: io.StringIO,
    ) -> None:
        args = Namespace(
            workspace=".",
            model="gpt-5.3-codex",
            commit_model="",
            commit_phase=False,
            commit_stall_timeout=300.0,
            commit_ttl=1800.0,
            poll=1.0,
            stall_timeout=600.0,
            task_ttl=21600.0,
            max_restarts=2,
            report_interval=2.0,
            summary_lines=25,
            nudge_after=10,
            nudge_cooldown=300.0,
            nudge_text="continue",
            telegram_test=None,
            reinit_hooks=False,
            hooks=False,
            max_sessions=0,
            init_kanban=False,
            debug=False,
            agent_output_log=False,
            backend="cursor",
        )
        build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)

        result = cli_app.main()

        self.assertEqual(result, 1)
        crash_line = next((line for line in stdout_mock.getvalue().splitlines() if '"event": "orc_crash_report"' in line), "")
        self.assertTrue(crash_line)
        crash_payload = json.loads(crash_line)
        self.assertEqual(crash_payload.get("entrypoint"), "orc_core.cli_app:main")
        self.assertEqual(crash_payload.get("phase"), "main")
        self.assertEqual(crash_payload.get("exception_type"), "RuntimeError")
        self.assertEqual(crash_payload.get("error"), "boom")
        self.assertIn("RuntimeError: boom", crash_payload.get("traceback", ""))
        self.assertIn("RuntimeError: boom", stderr_mock.getvalue())


if __name__ == "__main__":
    unittest.main()
