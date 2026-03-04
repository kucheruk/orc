#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from orc_core.backlog_orchestrator import BacklogOrchestrator
from orc_core.quit_signal import (
    clear_stop_request,
    is_quit_after_task_requested,
    is_stop_requested,
)
from orc_core.task_execution import TaskExecutionResult
from orc_core.task_source import MarkdownTaskSource
from orc_core.tui_app import OrcApp


class _FakeEngine:
    def __init__(self, backlog_path: Path, *, committed: bool = True) -> None:
        self.backlog_path = backlog_path
        self.calls = []
        self.committed = committed

    def execute(self, request):
        self.calls.append(request)
        MarkdownTaskSource(self.backlog_path).mark_task_done(request.task.task_id)
        return TaskExecutionResult(status="completed", committed=self.committed)


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


class QuitAfterTaskTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_stop_request()

    def tearDown(self) -> None:
        clear_stop_request()

    def test_orc_app_action_toggles_quit_after_task_only(self) -> None:
        app = OrcApp(lambda _publish: 0)

        app.action_request_quit_after_task()

        self.assertTrue(is_quit_after_task_requested())
        self.assertFalse(is_stop_requested())
        app.action_request_quit_after_task()
        self.assertFalse(is_quit_after_task_requested())
        self.assertFalse(is_stop_requested())

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_orchestrator_stops_after_current_completed_task(self, hooks_config, hooks) -> None:
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

            app = OrcApp(lambda _publish: 0)
            app.action_request_quit_after_task()
            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-001"])

    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks")
    @patch("orc_core.backlog_orchestrator.ensure_repo_hooks_config")
    def test_orchestrator_does_not_stop_without_commit(self, hooks_config, hooks) -> None:
        hooks.return_value = (Path("/tmp/before.py"), Path("/tmp/stop.py"))
        hooks_config.return_value = Path("/tmp/hooks.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text(
                "- [ ] TASK-001 first\n"
                "- [ ] TASK-002 second\n",
                encoding="utf-8",
            )
            engine = _FakeEngine(backlog_path, committed=False)
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

            app = OrcApp(lambda _publish: 0)
            app.action_request_quit_after_task()
            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-001", "TASK-002"])


if __name__ == "__main__":
    unittest.main()
