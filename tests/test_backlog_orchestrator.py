#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core.backlog_orchestrator import BacklogOrchestrator
from orc_core.task_execution import TaskExecutionResult
from orc_core.task_source import MarkdownTaskSource


class _FakeEngine:
    def __init__(self, backlog_path: Path) -> None:
        self.backlog_path = backlog_path
        self.calls = []

    def execute(self, request):
        self.calls.append(request)
        MarkdownTaskSource(self.backlog_path).mark_task_done(request.task.task_id)
        return TaskExecutionResult(status="completed")


class _FailingEngine:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def execute(self, request):
        return TaskExecutionResult(status="failed", reason=self.reason)


class _ExplodingEngine:
    def execute(self, _request):
        raise RuntimeError("boom")


def _args(backlog: str) -> Namespace:
    return Namespace(
        mode="backlog",
        task_id="",
        backlog=backlog,
        model="gpt-5.2-codex",
        commit_model="",
        commit_phase=False,
        allow_fallback_commits=False,
        poll=0.01,
        stall_timeout=1.0,
        task_ttl=1.0,
        max_restarts=1,
        report_interval=0.1,
        summary_lines=5,
        nudge_after=5,
        nudge_cooldown=60.0,
        nudge_text="continue",
        commit_stall_timeout=1.0,
        commit_ttl=1.0,
        drop=False,
    )


class BacklogOrchestratorTest(unittest.TestCase):
    @patch("orc_core.backlog_orchestrator.cleanup_task_worktree")
    @patch("orc_core.backlog_orchestrator.create_task_worktree")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_orchestrator_uses_worktree_and_cleans_up_on_success(
        self,
        hooks_config,
        hooks,
        create_worktree,
        cleanup_worktree,
    ) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        create_worktree.return_value = SimpleNamespace(
            task_id="TASK-001",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001-1",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                use_task_worktrees=True,
                sleep_fn=lambda _seconds: None,
            )
            rc = orchestrator.run()
        self.assertEqual(rc, 0)
        create_worktree.assert_called_once()
        cleanup_worktree.assert_called_once()
        self.assertGreaterEqual(hooks.call_count, 2)
        self.assertEqual(hooks.call_args_list[0].args[0], tmpdir)
        self.assertEqual(hooks.call_args_list[1].args[0], "/tmp/repo/.orc/worktrees/TASK-001-1")

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_orchestrator_runs_until_backlog_complete(self, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text(
                "- [ ] TASK-001 first\n"
                "- [ ] TASK-002 second\n",
                encoding="utf-8",
            )
            engine = _FakeEngine(backlog_path)
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-001", "TASK-002"])
        hooks.assert_called()

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_orchestrator_exits_immediately_for_completed_backlog(self, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] TASK-001 done\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual(engine.calls, [])
        hooks.assert_called_once_with(tmpdir)
        hooks_config.assert_called_once()

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_request_contains_progress_values(self, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 only\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual(len(engine.calls), 1)
        self.assertEqual(engine.calls[0].progress_done, 0)
        self.assertEqual(engine.calls[0].progress_total, 1)
        self.assertFalse(engine.calls[0].allow_fallback_commits)
        self.assertEqual(engine.calls[0].agent_env["ORC_BASE_WORKSPACE"], tmpdir)
        self.assertEqual(engine.calls[0].agent_env["ORC_TASK_FILE"], str(Path(tmpdir) / ".cursor" / "orc-task.json"))
        self.assertEqual(
            engine.calls[0].agent_env["ORC_TASK_RUNTIME_FILE"],
            str(Path(tmpdir) / ".cursor" / "orc-task-runtime.json"),
        )

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_request_propagates_allow_fallback_commits_flag(self, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 only\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            args = _args("BACKLOG.md")
            args.allow_fallback_commits = True
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=args,
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual(len(engine.calls), 1)
        self.assertTrue(engine.calls[0].allow_fallback_commits)

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_single_mode_runs_selected_task_once(self, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text(
                "- [ ] TASK-001 first\n"
                "- [ ] TASK-002 second\n",
                encoding="utf-8",
            )
            engine = _FakeEngine(backlog_path)
            args = _args("BACKLOG.md")
            args.mode = "single"
            args.task_id = "TASK-002"
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=args,
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-002"])

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    @patch("orc_core.backlog_orchestrator.ui_error")
    def test_failed_execution_exposes_failure_reason(self, ui_error, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=_FailingEngine(reason="missing_conversation_id"),
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 1)
        self.assertEqual(orchestrator.last_failure_reason, "missing_conversation_id")
        ui_error.assert_called_once()
        self.assertIn("missing_conversation_id", ui_error.call_args.args[0])

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    @patch("orc_core.backlog_orchestrator.ui_error")
    def test_worktree_base_invariant_failure_reason_is_exposed(self, ui_error, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=_FailingEngine(reason="worktree_not_integrated_to_base"),
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 1)
        self.assertEqual(orchestrator.last_failure_reason, "worktree_not_integrated_to_base")
        ui_error.assert_called_once()
        self.assertIn("worktree_not_integrated_to_base", ui_error.call_args.args[0])

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    @patch("orc_core.backlog_orchestrator.ui_error")
    def test_unexpected_engine_exception_is_converted_to_failed_result(self, ui_error, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                task_path=Path(tmpdir) / ".cursor" / "orc-task.json",
                run_root=Path(tmpdir) / ".orc" / "run",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=_ExplodingEngine(),
                use_task_worktrees=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 1)
        self.assertEqual(orchestrator.last_failure_reason, "unexpected_engine_exception:RuntimeError")
        ui_error.assert_called_once()
        self.assertIn("unexpected_engine_exception:RuntimeError", ui_error.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
