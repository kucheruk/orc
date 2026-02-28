#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
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


def _args(backlog: str) -> Namespace:
    return Namespace(
        backlog=backlog,
        model="gpt-5.2-codex",
        commit_model="",
        commit_phase=False,
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
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual([call.task.task_id for call in engine.calls], ["TASK-001", "TASK-002"])

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
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual(engine.calls, [])

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
                sleep_fn=lambda _seconds: None,
            )

            rc = orchestrator.run()

        self.assertEqual(rc, 0)
        self.assertEqual(len(engine.calls), 1)
        self.assertEqual(engine.calls[0].progress_done, 0)
        self.assertEqual(engine.calls[0].progress_total, 1)


if __name__ == "__main__":
    unittest.main()
