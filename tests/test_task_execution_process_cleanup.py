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
        self.run_token = "run-token-task-exec"
        self._stop_calls = 0
        self.started_at = 0.0
        self.result_status = None
        self.stderr_count = 0
        self.last_stderr_line = ""

    def stop(self) -> None:
        self._stop_calls += 1

    def get_summary_text(self) -> str:
        return ""

    def maybe_report(self): pass
    def refresh_process_status(self): return None
    def force_finalize_live_tool_calls(self, reason): return {}
    def active_tool_calls_watchdog_snapshot(self): return {}


class _FakeWorker:
    def __init__(self) -> None:
        self.monitor = _FakeMonitor()

    def launch(self, _config):
        return self.monitor


class TaskExecutionProcessCleanupTest(unittest.TestCase):
    def _request(self, tmpdir: str, lifecycle: FakeLifecycle) -> TaskExecutionRequest:
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
                model="gpt-5.3-codex",
                commit_model="gpt-5.3-codex",
                merge_expert_model="gpt-5.3-codex",
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
            process_lifecycle=lifecycle,
        )

    def test_execute_cleans_up_monitor_when_wait_raises_keyboard_interrupt(self) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        lifecycle = FakeLifecycle()
        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, lifecycle)
            with patch("orc_core.tasks.execution.resume.write_task_file"), patch(
                "orc_core.tasks.execution.stage_loop.update_task_restart_count"
            ), patch(
                "orc_core.tasks.execution.launch.wait_for_completion",
                side_effect=KeyboardInterrupt,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    engine.execute(request)
        self.assertEqual(worker.monitor._stop_calls, 1)
        self.assertEqual(len(lifecycle.kill_tree_calls), 1)
        self.assertEqual(len(lifecycle.sweep_orphans_calls), 1)

    def test_execute_prefers_process_group_cleanup(self) -> None:
        worker = _FakeWorker()
        worker.monitor.process_group_id = 4242
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        lifecycle = FakeLifecycle()
        lifecycle.terminate_group_returns = True
        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, lifecycle)
            with patch("orc_core.tasks.execution.resume.write_task_file"), patch(
                "orc_core.tasks.execution.stage_loop.update_task_restart_count"
            ), patch(
                "orc_core.tasks.execution.launch.wait_for_completion",
                side_effect=KeyboardInterrupt,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    engine.execute(request)
        self.assertEqual(lifecycle.terminate_group_calls, [(4242, Path("/tmp/orc.log"), "agent")])
        self.assertEqual(lifecycle.kill_tree_calls, [])
        self.assertEqual(len(lifecycle.sweep_orphans_calls), 1)
        self.assertEqual(lifecycle.sweep_orphans_calls[0]["run_token"], "run-token-task-exec")

    def test_execute_falls_back_to_process_tree_cleanup_when_group_cleanup_not_applied(self) -> None:
        worker = _FakeWorker()
        worker.monitor.process_group_id = 4242
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        lifecycle = FakeLifecycle()
        lifecycle.terminate_group_returns = False
        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, lifecycle)
            with patch("orc_core.tasks.execution.resume.write_task_file"), patch(
                "orc_core.tasks.execution.stage_loop.update_task_restart_count"
            ), patch(
                "orc_core.tasks.execution.launch.wait_for_completion",
                side_effect=KeyboardInterrupt,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    engine.execute(request)
        self.assertEqual(lifecycle.terminate_group_calls, [(4242, Path("/tmp/orc.log"), "agent")])
        self.assertEqual(lifecycle.kill_tree_calls, [(12345, Path("/tmp/orc.log"), "agent")])
        self.assertEqual(len(lifecycle.sweep_orphans_calls), 1)
        self.assertEqual(lifecycle.sweep_orphans_calls[0]["run_token"], "run-token-task-exec")


if __name__ == "__main__":
    unittest.main()
