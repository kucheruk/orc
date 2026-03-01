#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from orc_core.backlog_orchestrator import BacklogOrchestrator
from orc_core.task_execution import TaskExecutionResult
from orc_core.task_source import MarkdownTaskSource


class _Engine:
    def __init__(self, backlog_path: Path) -> None:
        self.backlog_path = backlog_path
        self.calls: list[str] = []

    def execute(self, request):
        self.calls.append(request.task.task_id)
        MarkdownTaskSource(self.backlog_path).mark_task_done(request.task.task_id)
        return TaskExecutionResult(status="completed")


def _args() -> Namespace:
    return Namespace(
        mode="backlog",
        task_id="TASK-002",
        backlog="BACKLOG.md",
        model="gpt-5.3-codex",
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


class BacklogModeCycleGuardTest(unittest.TestCase):
    def test_backlog_mode_ignores_task_id_and_continues_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 a\n- [ ] TASK-002 b\n", encoding="utf-8")
            engine = _Engine(backlog_path)
            orchestrator = BacklogOrchestrator(
                workdir=tmpdir,
                backlog_path=backlog_path,
                args=_args(),
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
        self.assertEqual(engine.calls, ["TASK-001", "TASK-002"])


if __name__ == "__main__":
    unittest.main()
