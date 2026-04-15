#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.tasks.execution.engine import TaskExecutionEngine
from orc_core.tasks.execution.config import ModelConfig, TemplateConfig, TimingConfig
from orc_core.tasks.execution.request import TaskExecutionRequest
from orc_core.models.task_dto import Task


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
    def __init__(self) -> None:
        self.launch_calls = 0

    def launch(self, _config):
        self.launch_calls += 1
        return _FakeMonitor()

class TaskExecutionResumeStateTest(unittest.TestCase):
    def _request(self, tmpdir: str) -> TaskExecutionRequest:
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
                nudge_cooldown=60.0,
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
        )

    @patch("orc_core.tasks.task_agent_phases.kill_process_tree")
    @patch("orc_core.tasks.execution.engine.update_task_restart_count")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    def test_blank_resume_id_auto_drops_and_starts_fresh(self, write_task_file, *_mocks) -> None:
        """Blank conversation_id + restart_count=0 means the task never ran.
        Auto-drop stale state and start fresh instead of failing."""
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"   "}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.tasks.task_agent_phases.kill_process_tree")
    @patch("orc_core.tasks.execution.engine.update_task_restart_count")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    def test_blank_resume_id_with_restarts_auto_drops(self, write_task_file, *_mocks) -> None:
        """Blank conversation_id + restart_count>0: agent was killed before hook
        could write conversation_id. Auto-drop and start fresh."""
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"   ","restart_count":1}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)


if __name__ == "__main__":
    unittest.main()
