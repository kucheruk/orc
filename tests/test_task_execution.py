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
    def __init__(self) -> None:
        self.launch_calls = 0
        self.launch_kwargs: list[dict] = []

    def launch(self, **kwargs):
        self.launch_calls += 1
        self.launch_kwargs.append(kwargs)
        return _FakeMonitor()


class TaskExecutionEngineTest(unittest.TestCase):
    def _request(self, tmpdir: str, *, max_restarts: int = 2, commit_phase: bool = False) -> TaskExecutionRequest:
        root = Path(tmpdir)
        backlog_path = root / "BACKLOG.md"
        backlog_path.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")
        return TaskExecutionRequest(
            task=Task(task_id="TASK-001", text="test task", done=False),
            backlog_path=backlog_path,
            backlog_arg="BACKLOG.md",
            task_path=root / ".cursor" / "orc-task.json",
            workdir=tmpdir,
            run_root=root / ".orc" / "run",
            model="gpt-5.2-codex",
            commit_model="gpt-5.2-codex",
            prompt_template="{task_id} {task_text}",
            continue_template="continue {task_id}",
            commit_template="commit {task_id}",
            commit_phase=commit_phase,
            poll=0.01,
            stall_timeout=1.0,
            task_ttl=1.0,
            max_restarts=max_restarts,
            report_interval=0.1,
            summary_lines=5,
            nudge_after=5,
            nudge_cooldown=60.0,
            nudge_text="continue",
            commit_stall_timeout=1.0,
            commit_ttl=1.0,
            progress_done=0,
            progress_total=1,
        )

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    def test_restart_loop_completes_on_second_attempt(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["stalled", "completed"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, max_restarts=2))

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    def test_restart_loop_fails_after_max_restarts(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["stalled", "stalled"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, max_restarts=1))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "max_restarts_exceeded")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.task_execution._run_commit_phase", return_value=False)
    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    def test_commit_phase_failure_returns_failed_status(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, commit_phase=True))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "commit_phase_failed")

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.get_resume_id_from_agent_ls", return_value=None)
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    @patch("orc_core.task_execution.write_task_file")
    def test_missing_resume_id_resets_state_and_restarts_fresh(self, write_task_file, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s"}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)
        write_task_file.assert_called_once()
        self.assertFalse(worker.launch_kwargs[0].get("resume_latest"))


if __name__ == "__main__":
    unittest.main()
