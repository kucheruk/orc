#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core import cli_app


def _base_args(**overrides) -> Namespace:
    defaults = dict(
        backlog="BACKLOG.md",
        task="",
        workspace=".",
        model="gpt-5.3-codex",
        prompt_default="",
        prompt_template="",
        continue_template="",
        commit_template="",
        commit_model="",
        commit_phase=True,
        allow_fallback_commits=False,
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
        drop=False,
        mode="backlog",
        task_id="",
        prompt="",
        debug=False,
        agent_output_log=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


class CliPromptDefaultParserTest(unittest.TestCase):
    def test_parser_accepts_prompt_default_flag(self) -> None:
        parsed = cli_app.build_parser().parse_args(["--prompt-default", "specs/TASK.md"])
        self.assertEqual(parsed.prompt_default, "specs/TASK.md")

    def test_parser_prompt_default_defaults_to_empty(self) -> None:
        parsed = cli_app.build_parser().parse_args([])
        self.assertEqual(parsed.prompt_default, "")


class CliPromptDefaultMissingFileTest(unittest.TestCase):
    @patch("orc_core.cli_app.ui_error")
    @patch("orc_core.cli_app.ui_info")
    @patch("orc_core.cli_app.ensure_agent_installed")
    @patch("orc_core.cli_app.build_parser")
    def test_main_exits_2_when_prompt_default_file_missing(
        self,
        build_parser_mock,
        _ensure_agent_mock,
        _ui_info_mock,
        ui_error_mock,
    ) -> None:
        args = _base_args(prompt_default="/nonexistent/prompt.md")
        build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)

        result = cli_app.main()

        self.assertEqual(result, 2)
        ui_error_mock.assert_called_once()
        self.assertIn("--prompt-default", ui_error_mock.call_args[0][0])


class CliPromptDefaultOverrideTest(unittest.TestCase):
    @patch("orc_core.cli_app.detect_base_branch", return_value="master")
    @patch("orc_core.cli_app.release_lock")
    @patch("orc_core.cli_app.acquire_lock")
    @patch("orc_core.cli_app._cleanup_stale_task_file")
    @patch("orc_core.cli_app._validate_inputs", return_value=True)
    @patch("orc_core.cli_app._resolve_backlog")
    @patch("orc_core.cli_app.init_debug_logging", return_value=None)
    @patch("orc_core.cli_app._resolve_model")
    @patch("orc_core.cli_app.ensure_agent_installed")
    @patch("orc_core.cli_app.OrcApp")
    @patch("orc_core.cli_app.BacklogOrchestrator")
    @patch("orc_core.cli_app.TaskExecutionEngine")
    @patch("orc_core.cli_app.build_parser")
    def test_prompt_default_overrides_all_prompts(
        self,
        build_parser_mock,
        _engine_mock,
        orchestrator_cls_mock,
        orc_app_cls_mock,
        _ensure_agent_mock,
        _resolve_model_mock,
        _init_debug_mock,
        resolve_backlog_mock,
        _validate_mock,
        _cleanup_mock,
        _acquire_mock,
        _release_mock,
        _detect_branch_mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "universal.md"
            prompt_file.write_text("UNIVERSAL PROMPT", encoding="utf-8")
            args = _base_args(prompt_default=str(prompt_file), commit_phase=True)
            build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)
            resolve_backlog_mock.return_value = (Path("BACKLOG.md"), None)
            orchestrator_cls_mock.return_value = SimpleNamespace(
                last_failure_reason="", run_async=lambda: None,
            )
            orc_app_instance = orc_app_cls_mock.return_value
            orc_app_instance.run.return_value = 0
            orc_app_instance.last_error = None

            cli_app.main()

            _, kwargs = orchestrator_cls_mock.call_args
            self.assertEqual(kwargs["prompt_template"], "UNIVERSAL PROMPT")
            self.assertEqual(kwargs["continue_template"], "UNIVERSAL PROMPT")
            self.assertEqual(kwargs["commit_template"], "UNIVERSAL PROMPT")
            self.assertEqual(kwargs["merge_expert_template"], "UNIVERSAL PROMPT")
            self.assertEqual(kwargs["main_branch"], "master")

    @patch("orc_core.cli_app.release_lock")
    @patch("orc_core.cli_app.acquire_lock")
    @patch("orc_core.cli_app._cleanup_stale_task_file")
    @patch("orc_core.cli_app._validate_inputs", return_value=True)
    @patch("orc_core.cli_app._resolve_backlog")
    @patch("orc_core.cli_app.init_debug_logging", return_value=None)
    @patch("orc_core.cli_app._resolve_model")
    @patch("orc_core.cli_app.ensure_agent_installed")
    @patch("orc_core.cli_app.OrcApp")
    @patch("orc_core.cli_app.BacklogOrchestrator")
    @patch("orc_core.cli_app.TaskExecutionEngine")
    @patch("orc_core.cli_app.build_parser")
    def test_specific_template_takes_priority_over_prompt_default(
        self,
        build_parser_mock,
        _engine_mock,
        orchestrator_cls_mock,
        orc_app_cls_mock,
        _ensure_agent_mock,
        _resolve_model_mock,
        _init_debug_mock,
        resolve_backlog_mock,
        _validate_mock,
        _cleanup_mock,
        _acquire_mock,
        _release_mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            default_file = Path(tmpdir) / "universal.md"
            default_file.write_text("UNIVERSAL PROMPT", encoding="utf-8")
            specific_file = Path(tmpdir) / "specific_coder.md"
            specific_file.write_text("SPECIFIC CODER", encoding="utf-8")
            args = _base_args(
                prompt_default=str(default_file),
                prompt_template=str(specific_file),
                commit_phase=True,
            )
            build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)
            resolve_backlog_mock.return_value = (Path("BACKLOG.md"), None)
            orchestrator_cls_mock.return_value = SimpleNamespace(
                last_failure_reason="", run_async=lambda: None,
            )
            orc_app_instance = orc_app_cls_mock.return_value
            orc_app_instance.run.return_value = 0
            orc_app_instance.last_error = None

            cli_app.main()

            _, kwargs = orchestrator_cls_mock.call_args
            self.assertEqual(kwargs["prompt_template"], "SPECIFIC CODER")
            self.assertEqual(kwargs["continue_template"], "UNIVERSAL PROMPT")
            self.assertEqual(kwargs["commit_template"], "UNIVERSAL PROMPT")
            self.assertEqual(kwargs["merge_expert_template"], "UNIVERSAL PROMPT")

    @patch("orc_core.cli_app.ui_info")
    @patch("orc_core.cli_app.ensure_agent_installed")
    @patch("orc_core.cli_app.build_parser")
    def test_prompt_default_shows_ui_info(
        self,
        build_parser_mock,
        _ensure_agent_mock,
        ui_info_mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "custom.md"
            prompt_file.write_text("CUSTOM", encoding="utf-8")
            args = _base_args(prompt_default=str(prompt_file))
            build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)

            cli_app.main()

            info_calls = [c[0][0] for c in ui_info_mock.call_args_list]
            matching = [c for c in info_calls if "prompt default:" in c]
            self.assertTrue(matching, f"Expected ui_info with prompt default path, got: {info_calls}")
            self.assertIn(str(prompt_file), matching[0])


if __name__ == "__main__":
    unittest.main()
