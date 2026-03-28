#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.task_execution import TaskExecutionEngine, TaskExecutionRequest
from orc_core.task_source import Task


class _FakeProc:
    pid = 12345
    returncode = 0

    def poll(self):
        return None


class _FakeMetrics:
    total_lines = 1
    command_count = 1
    total_output_chars = 1
    tokens_total = 1
    files_edited = 1


class _FakeMonitor:
    def __init__(self) -> None:
        self.proc = _FakeProc()
        self.init_pid = None
        self.metrics = _FakeMetrics()
        self.last_output_time = 0.0
        self.ui_followup_prompt = False
        self.workdir = ""

    def stop(self) -> None:
        return None

    def get_summary_text(self) -> str:
        return "done"


class _FakeWorker:
    def launch(self, **_kwargs):
        return _FakeMonitor()


def _request(tmpdir: str) -> TaskExecutionRequest:
    root = Path(tmpdir)
    backlog_path = root / "BACKLOG.md"
    backlog_path.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")
    return TaskExecutionRequest(
        task=Task(task_id="TASK-001", text="test task", done=False),
        backlog_path=backlog_path,
        backlog_arg="BACKLOG.md",
        task_path=root / ".cursor" / "orc-task.json",
        workdir=tmpdir,
        base_workdir=tmpdir,
        run_root=root / ".orc" / "run",
        model="gpt-5.2-codex",
        commit_model="gpt-5.2-codex",
        merge_expert_model="gpt-5.2-codex",
        prompt_template="{task_id} {task_text}",
        continue_template="continue {task_id} :: {reason}",
        commit_template="commit {task_id}",
        merge_expert_template="merge {task_id}",
        commit_phase=False,
        integrate_to_main=False,
        main_branch="main",
        allow_fallback_commits=False,
        poll=0.01,
        stall_timeout=1.0,
        task_ttl=1.0,
        max_restarts=1,
        report_interval=0.1,
        summary_lines=5,
        nudge_after=5,
        nudge_cooldown=7.0,
        nudge_text="continue",
        commit_stall_timeout=1.0,
        commit_ttl=1.0,
        progress_done=0,
        progress_total=1,
        agent_output_log_path=None,
    )


class WaitingForInputNoticeTest(unittest.TestCase):
    def setUp(self):
        self._tg_patcher = patch("orc_core.task_execution.send_telegram_message")
        self._tg_mock = self._tg_patcher.start()

    def tearDown(self):
        self._tg_patcher.stop()
    @patch("orc_core.task_execution._cleanup_monitor_processes")
    @patch("orc_core.task_execution.wait_for_completion", return_value="waiting_for_input")
    @patch("orc_core.task_execution.ui_warn")
    def test_waiting_for_input_prints_visible_status(self, ui_warn_mock, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(_request(tmpdir))

        self.assertEqual(result.status, "continue")
        self.assertEqual(result.reason, "waiting_for_input")
        self.assertEqual(result.delay_seconds, 7.0)
        ui_warn_mock.assert_called_once()
        self.assertIn("follow-up", ui_warn_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
