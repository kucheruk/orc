#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.task_execution import TaskExecutionEngine, TaskExecutionRequest
from orc_core.task_source import Task


class _FakeMonitor:
    class _Proc:
        pid = 12345
        returncode = 0

        def poll(self):
            return None

    class _Metrics:
        total_lines = 0
        command_count = 0
        total_output_chars = 0
        tokens_total = 0
        files_edited = 0

    def __init__(self) -> None:
        self.proc = self._Proc()
        self.init_pid = None
        self.process_group_id = None
        self.metrics = self._Metrics()
        self.last_output_time = 0.0
        self.ui_followup_prompt = False
        self.workdir = ""
        self._stop_calls = 0

    def stop(self) -> None:
        self._stop_calls += 1

    def get_summary_text(self) -> str:
        return ""


class _FakeWorker:
    def __init__(self) -> None:
        self.monitor = _FakeMonitor()

    def launch(self, **_kwargs):
        return self.monitor


class TaskExecutionProcessCleanupTest(unittest.TestCase):
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
            run_root=root / ".orc" / "run",
            model="gpt-5.3-codex",
            commit_model="gpt-5.3-codex",
            prompt_template="{task_id} {task_text}",
            continue_template="continue {task_id} :: {reason}",
            commit_template="commit {task_id}",
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
            progress_done=0,
            progress_total=1,
            agent_output_log_path=None,
        )

    def test_execute_cleans_up_monitor_when_wait_raises_keyboard_interrupt(self) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            with patch("orc_core.task_execution.write_task_file"), patch(
                "orc_core.task_execution.update_task_restart_count"
            ), patch(
                "orc_core.task_execution.wait_for_completion",
                side_effect=KeyboardInterrupt,
            ), patch(
                "orc_core.task_execution.kill_orphan_project_processes"
            ) as orphan_sweep_mock, patch(
                "orc_core.task_execution.kill_process_tree"
            ) as kill_mock:
                with self.assertRaises(KeyboardInterrupt):
                    engine.execute(request)
        self.assertEqual(worker.monitor._stop_calls, 1)
        kill_mock.assert_called_once()
        orphan_sweep_mock.assert_called_once()

    def test_execute_prefers_process_group_cleanup(self) -> None:
        worker = _FakeWorker()
        worker.monitor.process_group_id = 4242
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            with patch("orc_core.task_execution.write_task_file"), patch(
                "orc_core.task_execution.update_task_restart_count"
            ), patch(
                "orc_core.task_execution.wait_for_completion",
                side_effect=KeyboardInterrupt,
            ), patch(
                "orc_core.task_execution.terminate_process_group",
                return_value=True,
            ) as terminate_group_mock, patch(
                "orc_core.task_execution.kill_orphan_project_processes"
            ) as orphan_sweep_mock, patch(
                "orc_core.task_execution.kill_process_tree"
            ) as kill_mock:
                with self.assertRaises(KeyboardInterrupt):
                    engine.execute(request)
        terminate_group_mock.assert_called_once_with(4242, Path("/tmp/orc.log"), label="agent")
        kill_mock.assert_not_called()
        orphan_sweep_mock.assert_called_once()

    def test_execute_falls_back_to_process_tree_cleanup_when_group_cleanup_not_applied(self) -> None:
        worker = _FakeWorker()
        worker.monitor.process_group_id = 4242
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            with patch("orc_core.task_execution.write_task_file"), patch(
                "orc_core.task_execution.update_task_restart_count"
            ), patch(
                "orc_core.task_execution.wait_for_completion",
                side_effect=KeyboardInterrupt,
            ), patch(
                "orc_core.task_execution.terminate_process_group",
                return_value=False,
            ) as terminate_group_mock, patch(
                "orc_core.task_execution.kill_orphan_project_processes"
            ) as orphan_sweep_mock, patch(
                "orc_core.task_execution.kill_process_tree"
            ) as kill_mock:
                with self.assertRaises(KeyboardInterrupt):
                    engine.execute(request)
        terminate_group_mock.assert_called_once_with(4242, Path("/tmp/orc.log"), label="agent")
        kill_mock.assert_called_once_with(12345, Path("/tmp/orc.log"), label="agent")
        orphan_sweep_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

