#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
import io
from argparse import Namespace
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core import cli_app
from orc_core.cli_app import _failure_message, _resolve_mode, _resolve_model, _resumable_task_id
from orc_core.model_selector import DEFAULT_MODEL
from orc_core.model_selector import ModelSelectionError
from orc_core.start_menu import StartMenuChoice


def _args() -> Namespace:
    return Namespace(
        mode="",
        task_id="",
        prompt="",
        task="",
        model="",
        debug=False,
    )


class CliAppModeSelectionTest(unittest.TestCase):
    def test_parser_supports_agent_output_log_flag(self) -> None:
        parsed = cli_app.build_parser().parse_args(["--agent-output-log"])
        self.assertTrue(parsed.agent_output_log)

    def test_parser_fallback_commits_default_is_disabled(self) -> None:
        parsed = cli_app.build_parser().parse_args([])
        self.assertFalse(parsed.allow_fallback_commits)

    def test_parser_supports_enabling_fallback_commits(self) -> None:
        parsed = cli_app.build_parser().parse_args(["--allow-fallback-commits"])
        self.assertTrue(parsed.allow_fallback_commits)

    def test_parser_supports_disabling_fallback_commits(self) -> None:
        parsed = cli_app.build_parser().parse_args(["--allow-fallback-commits", "--no-allow-fallback-commits"])
        self.assertFalse(parsed.allow_fallback_commits)

    @patch("orc_core.cli_app.show_start_menu")
    def test_legacy_task_promotes_to_prompt_mode(self, show_start_menu) -> None:
        args = _args()
        args.task = "do thing"

        _resolve_mode(args, Path("BACKLOG.md"))

        self.assertEqual(args.mode, "prompt")
        self.assertEqual(args.prompt, "do thing")
        show_start_menu.assert_not_called()

    @patch("orc_core.cli_app.show_start_menu")
    def test_explicit_task_id_uses_single_mode_without_menu(self, show_start_menu) -> None:
        args = _args()
        args.task_id = "TASK-001"

        _resolve_mode(args, Path("BACKLOG.md"))

        self.assertEqual(args.mode, "single")
        show_start_menu.assert_not_called()

    @patch("orc_core.cli_app.show_start_menu")
    def test_menu_choice_populates_mode_values(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="single", task_id="TASK-002", model="gpt-5.3-codex")

        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
            )

        self.assertEqual(args.mode, "single")
        self.assertEqual(args.task_id, "TASK-002")
        self.assertEqual(args.model, "gpt-5.3-codex")

    @patch("orc_core.cli_app.show_start_menu")
    def test_resume_mode_choice_maps_to_backlog_mode(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="resume", task_id="TASK-002", model="gpt-5.3-codex")

        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
            )

        self.assertEqual(args.mode, "backlog")


class CliAppModelSelectionTest(unittest.TestCase):
    @patch("orc_core.cli_app.save_last_selected_model")
    def test_interactive_selection_persists_selected_model(self, save_last_selected_model) -> None:
        args = _args()
        args.model = "sonnet-4.5"

        _resolve_model(args, "/tmp/workspace", interactive_requested=True, model_loader=None)

        self.assertEqual(args.model, "sonnet-4.5")
        save_last_selected_model.assert_called_once_with("/tmp/workspace", "sonnet-4.5")

    @patch("orc_core.cli_app.save_last_selected_model")
    def test_non_interactive_without_explicit_model_uses_default(
        self,
        save_last_selected_model,
    ) -> None:
        args = _args()

        _resolve_model(args, "/tmp/workspace", interactive_requested=False, model_loader=None)

        self.assertEqual(args.model, DEFAULT_MODEL)
        save_last_selected_model.assert_not_called()

    def test_interactive_requires_preselected_model(self) -> None:
        args = _args()
        with self.assertRaises(ModelSelectionError):
            _resolve_model(args, "/tmp/workspace", interactive_requested=True, model_loader=None)


class CliAppFailureMessageTest(unittest.TestCase):
    def test_missing_conversation_id_includes_drop_hint(self) -> None:
        message = _failure_message("missing_conversation_id")
        self.assertIn("--drop", message)
        self.assertIn("conversation_id", message)

    def test_unknown_failure_reason_is_included(self) -> None:
        message = _failure_message("custom_reason")
        self.assertIn("custom_reason", message)


class CliAppResumeDetectionTest(unittest.TestCase):
    def test_resumable_task_id_returns_task_when_payload_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backlog = root / "BACKLOG.md"
            backlog.write_text("- [ ] TASK-001 keep going\n", encoding="utf-8")
            task_path = root / ".cursor" / "orc-task.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001",
                        "conversation_id": "conv-123",
                        "backlog_path": str(backlog),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            detected = _resumable_task_id(task_path, backlog)

        self.assertEqual(detected, "TASK-001")

    def test_resumable_task_id_returns_empty_when_task_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backlog = root / "BACKLOG.md"
            backlog.write_text("- [x] TASK-001 done\n", encoding="utf-8")
            task_path = root / ".cursor" / "orc-task.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001",
                        "conversation_id": "conv-123",
                        "backlog_path": str(backlog),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            detected = _resumable_task_id(task_path, backlog)

        self.assertEqual(detected, "")


class CliAppTuiMouseReportingTest(unittest.TestCase):
    @patch("orc_core.cli_app.release_lock")
    @patch("orc_core.cli_app.acquire_lock")
    @patch("orc_core.cli_app.load_prompt", return_value="template")
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
    def test_main_disables_mouse_reporting_for_tui_run(
        self,
        build_parser_mock,
        _engine_mock,
        orchestrator_cls_mock,
        orc_app_cls_mock,
        _ensure_agent_installed_mock,
        _resolve_model_mock,
        _init_debug_logging_mock,
        resolve_backlog_mock,
        _validate_inputs_mock,
        _cleanup_stale_task_file_mock,
        _load_prompt_mock,
        _acquire_lock_mock,
        _release_lock_mock,
    ) -> None:
        args = Namespace(
            backlog="BACKLOG.md",
            task="",
            workspace=".",
            model="gpt-5.3-codex",
            prompt_template="",
            continue_template="",
            commit_template="",
            commit_model="",
            commit_phase=False,
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
        build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)
        resolve_backlog_mock.return_value = (Path("BACKLOG.md"), None)
        orchestrator_cls_mock.return_value = SimpleNamespace(last_failure_reason="", run_async=lambda: None)
        orc_app_instance = orc_app_cls_mock.return_value
        orc_app_instance.run.return_value = 0
        orc_app_instance.last_error = None

        result = cli_app.main()

        self.assertEqual(result, 0)
        orc_app_instance.run.assert_called_once_with(mouse=False)


class CliAppCrashStdoutDiagnosticsTest(unittest.TestCase):
    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("orc_core.cli_app.ui_error")
    @patch("orc_core.cli_app.release_lock")
    @patch("orc_core.cli_app.acquire_lock")
    @patch("orc_core.cli_app.load_prompt", return_value="template")
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
    def test_main_emits_crash_json_to_stdout_when_orchestrator_worker_fails(
        self,
        build_parser_mock,
        _engine_mock,
        orchestrator_cls_mock,
        orc_app_cls_mock,
        _ensure_agent_installed_mock,
        _resolve_model_mock,
        _init_debug_logging_mock,
        resolve_backlog_mock,
        _validate_inputs_mock,
        _cleanup_stale_task_file_mock,
        _load_prompt_mock,
        _acquire_lock_mock,
        _release_lock_mock,
        _ui_error_mock,
        stdout_mock: io.StringIO,
        stderr_mock: io.StringIO,
    ) -> None:
        args = Namespace(
            backlog="BACKLOG.md",
            task="",
            workspace=".",
            model="gpt-5.3-codex",
            prompt_template="",
            continue_template="",
            commit_template="",
            commit_model="",
            commit_phase=False,
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
        build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)
        resolve_backlog_mock.return_value = (Path("BACKLOG.md"), None)
        orchestrator_cls_mock.return_value = SimpleNamespace(last_failure_reason="", run_async=lambda: None)
        orc_app_instance = orc_app_cls_mock.return_value
        orc_app_instance.run.return_value = 1
        orc_app_instance.last_error = "Traceback worker crash"

        result = cli_app.main()

        self.assertEqual(result, 1)
        crash_line = next((line for line in stdout_mock.getvalue().splitlines() if '"event": "orc_crash_report"' in line), "")
        self.assertTrue(crash_line)
        crash_payload = json.loads(crash_line)
        self.assertEqual(crash_payload.get("entrypoint"), "orc_core.cli_app:main")
        self.assertEqual(crash_payload.get("phase"), "orchestrator.run_async")
        self.assertEqual(crash_payload.get("exception_type"), "OrchestratorUnhandledException")
        self.assertIn("Traceback worker crash", crash_payload.get("traceback", ""))
        self.assertIn("Traceback worker crash", stderr_mock.getvalue())

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("orc_core.cli_app.ui_error")
    @patch("orc_core.cli_app.build_parser")
    @patch("orc_core.cli_app.ensure_agent_installed", side_effect=RuntimeError("boom"))
    def test_main_emits_crash_json_to_stdout_on_unhandled_exception(
        self,
        _ensure_agent_installed_mock,
        build_parser_mock,
        _ui_error_mock,
        stdout_mock: io.StringIO,
        stderr_mock: io.StringIO,
    ) -> None:
        args = Namespace(
            backlog="BACKLOG.md",
            task="",
            workspace=".",
            model="gpt-5.3-codex",
            prompt_template="",
            continue_template="",
            commit_template="",
            commit_model="",
            commit_phase=False,
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
