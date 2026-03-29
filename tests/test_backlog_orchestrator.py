#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core.quit_signal import clear_stop_request
from orc_core.session_manager import SessionManager
from orc_core.task_execution import TaskExecutionResult
from orc_core.task_source import MarkdownTaskSource


_NOOP_PUBLISHER = lambda _sid, _snap: None


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


class SessionManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_stop_request()

    @patch("orc_core.session_manager.cleanup_task_worktree")
    @patch("orc_core.session_manager.create_task_worktree")
    def test_orchestrator_uses_worktree_and_cleans_up_on_success(
        self,
        create_worktree,
        cleanup_worktree,
    ) -> None:
        create_worktree.return_value = SimpleNamespace(
            task_id="TASK-001",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001-1",
            branch_name="orc/TASK-001",
            base_workdir="/tmp/repo",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )
            rc = orchestrator.run(_NOOP_PUBLISHER)
        self.assertEqual(rc, 0)
        create_worktree.assert_called_once()
        cleanup_worktree.assert_called_once()

    def test_orchestrator_runs_until_backlog_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text(
                "- [ ] TASK-001 first\n"
                "- [ ] TASK-002 second\n",
                encoding="utf-8",
            )
            engine = _FakeEngine(backlog_path)
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-001", "TASK-002"])

    def test_orchestrator_exits_immediately_for_completed_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] TASK-001 done\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 0)
        self.assertEqual(engine.calls, [])

    def test_request_contains_progress_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 only\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 0)
        self.assertEqual(len(engine.calls), 1)
        self.assertEqual(engine.calls[0].progress_done, 0)
        self.assertEqual(engine.calls[0].progress_total, 1)
        self.assertFalse(engine.calls[0].allow_fallback_commits)
        self.assertEqual(engine.calls[0].agent_env["ORC_BASE_WORKSPACE"], workdir)
        self.assertIn("active-task.json", engine.calls[0].agent_env["ORC_TASK_FILE"])
        self.assertIn("active-task-runtime.json", engine.calls[0].agent_env["ORC_TASK_RUNTIME_FILE"])

    def test_request_propagates_allow_fallback_commits_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 only\n", encoding="utf-8")
            engine = _FakeEngine(backlog_path)
            args = _args("BACKLOG.md")
            args.allow_fallback_commits = True
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=args,
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 0)
        self.assertEqual(len(engine.calls), 1)
        self.assertTrue(engine.calls[0].allow_fallback_commits)

    def test_single_mode_runs_selected_task_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text(
                "- [ ] TASK-001 first\n"
                "- [ ] TASK-002 second\n",
                encoding="utf-8",
            )
            engine = _FakeEngine(backlog_path)
            args = _args("BACKLOG.md")
            args.mode = "single"
            args.task_id = "TASK-002"
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=args,
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=engine,
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-002"])

    def test_failed_execution_exposes_failure_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=_FailingEngine(reason="missing_conversation_id"),
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 1)
        self.assertEqual(orchestrator.last_failure_reason, "missing_conversation_id")

    def test_worktree_base_invariant_failure_reason_is_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=_FailingEngine(reason="worktree_not_integrated_to_base"),
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 1)
        self.assertEqual(orchestrator.last_failure_reason, "worktree_not_integrated_to_base")

    def test_unexpected_engine_exception_is_converted_to_failed_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = str(Path(tmpdir).resolve())
            backlog_path = Path(workdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 first\n", encoding="utf-8")
            orchestrator = SessionManager(
                workdir=workdir,
                backlog_path=backlog_path,
                args=_args("BACKLOG.md"),
                log_path=Path(workdir) / ".orc" / "orc.log",
                prompt_template="{task_id}",
                continue_template="{task_id}",
                commit_template="{task_id}",
                engine=_ExplodingEngine(),
                integrate_to_main=False,
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run(_NOOP_PUBLISHER)

        self.assertEqual(rc, 1)
        self.assertEqual(orchestrator.last_failure_reason, "execution_crashed")


if __name__ == "__main__":
    unittest.main()
