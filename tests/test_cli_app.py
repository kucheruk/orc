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
from orc_core.cli_app import _failure_message, _resolve_mode, _resolve_model, _resumable_task_id, _validate_inputs
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
    def test_parser_debug_help_mentions_system_temp_directory(self) -> None:
        parser = cli_app.build_parser()
        debug_action = next((action for action in parser._actions if "--debug" in action.option_strings), None)
        self.assertIsNotNone(debug_action)
        self.assertIn("system temp directory", str(debug_action.help))

    def test_parser_supports_agent_output_log_flag(self) -> None:
        parsed = cli_app.build_parser().parse_args(["--agent-output-log"])
        self.assertTrue(parsed.agent_output_log)

    def test_parser_agent_output_log_help_mentions_system_temp_directory(self) -> None:
        parser = cli_app.build_parser()
        action = next((item for item in parser._actions if "--agent-output-log" in item.option_strings), None)
        self.assertIsNotNone(action)
        self.assertIn("system temp directory", str(action.help))

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
    def test_menu_status_line_passed_to_start_screen(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="single", task_id="TASK-002", model="gpt-5.3-codex")

        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
                status_line="Задача TASK-002 завершена успешно",
            )

        show_start_menu.assert_called_once()
        _, kwargs = show_start_menu.call_args
        self.assertEqual(kwargs["status_line"], "Задача TASK-002 завершена успешно")

    @patch("orc_core.cli_app.show_start_menu")
    def test_menu_receives_explicit_workdir(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="backlog", model="gpt-5.3-codex")
        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
                workdir=tmpdir,
            )
        _, kwargs = show_start_menu.call_args
        self.assertEqual(kwargs["workdir"], tmpdir)

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


class CliAppStageSpecsBuilderTest(unittest.TestCase):
    def _cfg(self, *, enabled: bool, model: str, prompt: str):
        return SimpleNamespace(enabled=enabled, model=model, prompt=prompt)

    def test_build_stage_specs_respects_enabled_flags_and_keeps_required_stages(self) -> None:
        specs = cli_app._build_stage_specs(
            planning_config=self._cfg(enabled=True, model="m-plan", prompt="p-plan"),
            design_config=self._cfg(enabled=False, model="m-design", prompt="p-design"),
            coder_model="m-code",
            coder_prompt="p-code",
            review_config=self._cfg(enabled=True, model="m-review", prompt="p-review"),
            testing_config=self._cfg(enabled=False, model="m-test", prompt="p-test"),
            handoff_config=self._cfg(enabled=True, model="m-handoff", prompt="p-handoff"),
            commit_phase=True,
            default_handoff_model="m-default-handoff",
        )

        self.assertEqual([spec.stage_id for spec in specs], ["planning", "implementation", "review", "handoff"])
        self.assertEqual([spec.model for spec in specs], ["m-plan", "m-code", "m-review", "m-handoff"])

    def test_build_stage_specs_includes_design_and_testing_when_enabled(self) -> None:
        specs = cli_app._build_stage_specs(
            planning_config=self._cfg(enabled=False, model="m-plan", prompt="p-plan"),
            design_config=self._cfg(enabled=True, model="m-design", prompt="p-design"),
            coder_model="m-code",
            coder_prompt="p-code",
            review_config=self._cfg(enabled=False, model="m-review", prompt="p-review"),
            testing_config=self._cfg(enabled=True, model="m-test", prompt="p-test"),
            handoff_config=self._cfg(enabled=True, model="", prompt="p-handoff"),
            commit_phase=True,
            default_handoff_model="m-default-handoff",
        )

        self.assertEqual([spec.stage_id for spec in specs], ["design", "implementation", "testing", "handoff"])
        self.assertEqual(specs[-1].model, "m-default-handoff")


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


class CliAppInputValidationTest(unittest.TestCase):
    @patch("orc_core.cli_app.ui_error")
    def test_validate_inputs_accepts_gitignore_without_orc_rule(self, ui_error_mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".gitignore").write_text("bin/\nobj/\n", encoding="utf-8")
            backlog = root / "BACKLOG.md"
            backlog.write_text("- [ ] TASK-001 test\n", encoding="utf-8")
            args = Namespace(mode="backlog", task_id="")

            result = _validate_inputs(args, backlog, str(root), root / ".orc" / "orc.log")

        self.assertTrue(result)
        ui_error_mock.assert_not_called()

    @patch("orc_core.cli_app.ui_error")
    def test_validate_inputs_accepts_gitignore_with_orc_rule(self, ui_error_mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".gitignore").write_text(".orc/\n", encoding="utf-8")
            backlog = root / "BACKLOG.md"
            backlog.write_text("- [ ] TASK-001 test\n", encoding="utf-8")
            args = Namespace(mode="backlog", task_id="")

            result = _validate_inputs(args, backlog, str(root), root / ".orc" / "orc.log")

        self.assertTrue(result)
        ui_error_mock.assert_not_called()


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
    @patch("orc_core.cli_app.SessionManager")
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
            prompt_coder="",
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

    @patch("orc_core.cli_app.release_lock")
    @patch("orc_core.cli_app.acquire_lock")
    @patch("orc_core.cli_app.load_prompt", return_value="template")
    @patch("orc_core.cli_app._cleanup_stale_task_file")
    @patch("orc_core.cli_app._validate_inputs", return_value=True)
    @patch("orc_core.cli_app._resolve_backlog")
    @patch("orc_core.cli_app.init_debug_logging", return_value=None)
    @patch("orc_core.cli_app._resolve_model")
    @patch("orc_core.cli_app._resolve_mode")
    @patch("orc_core.cli_app.start_model_list_loading")
    @patch("orc_core.cli_app.ensure_agent_installed")
    @patch("orc_core.cli_app.OrcApp")
    @patch("orc_core.cli_app.SessionManager")
    @patch("orc_core.cli_app.TaskExecutionEngine")
    @patch("orc_core.cli_app.build_parser")
    def test_main_returns_to_menu_after_single_success(
        self,
        build_parser_mock,
        _engine_mock,
        orchestrator_cls_mock,
        orc_app_cls_mock,
        _ensure_agent_installed_mock,
        model_loader_mock,
        resolve_mode_mock,
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
            model="",
            prompt_coder="",
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
            mode="",
            task_id="",
            prompt="",
            debug=False,
            agent_output_log=False,
        )
        build_parser_mock.return_value = SimpleNamespace(parse_args=lambda: args)
        resolve_backlog_mock.return_value = (Path("BACKLOG.md"), None)
        orchestrator_cls_mock.return_value = SimpleNamespace(last_failure_reason="", run_async=lambda: None)
        model_loader_mock.return_value = SimpleNamespace(result=lambda timeout=30.0: ["gpt-5.3-codex"])
        call_index = {"value": 0}

        def _resolve_mode_side_effect(mut_args, *_args, **kwargs):
            status_line = kwargs.get("status_line", "")
            if call_index["value"] == 0:
                mut_args.mode = "single"
                mut_args.task_id = "TASK-009"
                mut_args.model = "gpt-5.3-codex"
                self.assertEqual(status_line, "")
            else:
                mut_args.mode = "backlog"
                mut_args.task_id = ""
                mut_args.model = "gpt-5.3-codex"
                self.assertEqual(status_line, "Задача TASK-009 завершена успешно")
            call_index["value"] += 1

        resolve_mode_mock.side_effect = _resolve_mode_side_effect
        orc_app_cls_mock.side_effect = [
            SimpleNamespace(run=lambda mouse=False: 0, last_error=None),
            SimpleNamespace(run=lambda mouse=False: 0, last_error=None),
        ]

        result = cli_app.main()

        self.assertEqual(result, 0)
        self.assertEqual(resolve_mode_mock.call_count, 2)
        self.assertEqual(orc_app_cls_mock.call_count, 2)


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
    @patch("orc_core.cli_app.SessionManager")
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
            prompt_coder="",
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
            prompt_coder="",
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
