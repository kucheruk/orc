#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.tasks.execution.engine import TaskExecutionEngine
from orc_core.tasks.execution.config import ModelConfig, TemplateConfig, TimingConfig
from orc_core.tasks.execution.request import TaskExecutionRequest
from orc_core.tasks.dto import Task
from tests._fake_lifecycle import FakeLifecycle


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
        self.process_group_id = None
        self.started_at = 0.0
        self.run_token = ""
        self.result_status = None
        self.stderr_count = 0
        self.last_stderr_line = ""

    def stop(self) -> None:
        return None

    def get_summary_text(self) -> str:
        return "done"


    def maybe_report(self): pass
    def refresh_process_status(self): return None
    def force_finalize_live_tool_calls(self, reason): return {}
    def active_tool_calls_watchdog_snapshot(self): return {}

class _FakeWorker:
    def launch(self, _config):
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
        timing=TimingConfig(
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
        ),
        models=ModelConfig(
            model="gpt-5.2-codex",
            commit_model="gpt-5.2-codex",
            merge_expert_model="gpt-5.2-codex",
        ),
        templates=TemplateConfig(
            prompt_template="{task_id} {task_text}",
            continue_template="continue {task_id} :: {reason}",
            commit_template="commit {task_id}",
            merge_expert_template="merge {task_id}",
        ),
        commit_phase=False,
        integrate_to_main=False,
        main_branch="main",
        allow_fallback_commits=False,
        progress_done=0,
        progress_total=1,
        agent_output_log_path=None,
        process_lifecycle=FakeLifecycle(),
    )

class WaitingForInputNoticeTest(unittest.TestCase):
    @patch("orc_core.tasks.execution.launch.cleanup_monitor_processes")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="waiting_for_input")
    @patch("orc_core.tasks.completion.handlers._logger")
    def test_waiting_for_input_prints_visible_status(self, logger_mock, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(_request(tmpdir))

        self.assertEqual(result.status, "continue")
        self.assertEqual(result.reason, "waiting_for_input")
        self.assertEqual(result.delay_seconds, 7.0)
        logger_mock.warning.assert_called_once()
        self.assertIn("follow-up", logger_mock.warning.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
