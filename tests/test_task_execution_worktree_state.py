#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from orc_core.tasks.execution.engine import TaskExecutionEngine
import orc_core.tasks.integration.main_integrator as main_integrator
import orc_core.tasks.execution.preflight as task_execution_preflight
from orc_core.tasks.execution.config import ModelConfig, TemplateConfig, TimingConfig
from orc_core.tasks.execution.request import TaskExecutionRequest
from orc_core.tasks.dto import Task
from types import SimpleNamespace
from orc_core.tasks.ports import PreflightResult
from orc_core.git.git_helpers import classify_main_integration_error
from tests._fake_lifecycle import FakeLifecycle, FakeStatePaths, FakeStateWriter


def _fake_preflight(*, ok: bool, error: str):
    result = PreflightResult(ok=ok, error=error)
    return SimpleNamespace(
        run=lambda **kwargs: result,
        classify_error=classify_main_integration_error,
    )


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


def _request(base_dir: Path, worktree_dir: Path) -> TaskExecutionRequest:
    backlog_path = base_dir / "BACKLOG.md"
    backlog_path.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")
    return TaskExecutionRequest(
        task=Task(task_id="TASK-001", text="test task", done=False),
        backlog_path=backlog_path,
        backlog_arg="BACKLOG.md",
        task_path=base_dir / ".cursor" / "orc-task.json",
        workdir=str(worktree_dir),
        base_workdir=str(base_dir),
        run_root=worktree_dir / ".orc" / "run",
        timing=TimingConfig(
            poll=0.01,
            stall_timeout=1.0,
            task_ttl=1.0,
            max_restarts=1,
            report_interval=0.1,
            summary_lines=5,
            nudge_after=5,
            nudge_cooldown=1.0,
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
        state_writer=FakeStateWriter(),
        state_paths=FakeStatePaths(base_dir),
    )

class TaskExecutionWorktreeStateTest(unittest.TestCase):
    @patch("orc_core.tasks.execution.launch.cleanup_monitor_processes")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="waiting_for_input")
    @patch("orc_core.notifications.notify.send_telegram_message")
    def test_writes_resume_state_in_base_workspace_and_avoids_duplicate_start_notifications(
        self,
        send_telegram_message_mock,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_dir = root / "base"
            worktree_dir = root / "worktree"
            base_dir.mkdir(parents=True, exist_ok=True)
            worktree_dir.mkdir(parents=True, exist_ok=True)
            request = _request(base_dir, worktree_dir)

            result_first = engine.execute(request)
            state = json.loads(request.task_path.read_text(encoding="utf-8"))
            state["conversation_id"] = "conv-1"
            request.task_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            result_second = engine.execute(request)

            self.assertEqual(result_first.status, "continue")
            self.assertEqual(result_second.status, "failed")
            self.assertEqual(result_second.reason, "max_restarts_exceeded")
            self.assertTrue(request.task_path.exists())
            state = json.loads(request.task_path.read_text(encoding="utf-8"))
            self.assertEqual(state["workspace_root"], str(base_dir))
            self.assertEqual(int(state.get("restart_count", -1)), 2)

        # Telegram notifications removed — kanban session manager handles them
        self.assertEqual(send_telegram_message_mock.call_count, 0)

    @patch("orc_core.tasks.execution.launch.cleanup_monitor_processes")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="stalled")
    @patch("orc_core.notifications.notify.send_telegram_message")
    def test_syncs_done_flag_from_worktree_backlog_into_base(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_dir = root / "base"
            worktree_dir = root / "worktree"
            base_dir.mkdir(parents=True, exist_ok=True)
            worktree_dir.mkdir(parents=True, exist_ok=True)
            request = _request(base_dir, worktree_dir)
            (worktree_dir / "BACKLOG.md").write_text("- [x] TASK-001 test task\n", encoding="utf-8")

            result = engine.execute(request)
            base_backlog = (base_dir / "BACKLOG.md").read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed")
        self.assertIn("[x] TASK-001", base_backlog)
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.tasks.integration.main_integrator.has_commits_ahead_of_branch", return_value=True)
    @patch("orc_core.tasks.integration.main_integrator.merge_task_branch_into_main")
    @patch("orc_core.tasks.execution.launch.cleanup_monitor_processes")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="process_exited")
    @patch("orc_core.notifications.notify.send_telegram_message")
    @patch("orc_core.tasks.execution.preflight._default_preflight")
    def test_does_not_mutate_base_backlog_when_runtime_done_and_integration_fails(self, mock_preflight, *_mocks) -> None:
        import orc_core.tasks.execution.engine as task_execution
        import orc_core.tasks.execution.finalize as task_execution_finalize

        mock_preflight.return_value = _fake_preflight(ok=True, error="")
        main_integrator.merge_task_branch_into_main.return_value = type(
            "Integration",
            (),
            {"ok": False, "conflict": False, "error": "checkout main failed: test"},
        )()
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_dir = root / "base"
            worktree_dir = root / "worktree"
            base_dir.mkdir(parents=True, exist_ok=True)
            worktree_dir.mkdir(parents=True, exist_ok=True)
            request = _request(base_dir, worktree_dir)
            request = replace(request, integrate_to_main=True, main_branch="main")
            (worktree_dir / "BACKLOG.md").write_text("- [x] TASK-001 test task\n", encoding="utf-8")

            result = engine.execute(request)
            base_backlog = (base_dir / "BACKLOG.md").read_text(encoding="utf-8")

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "main_integration_failed")
        self.assertIn("[ ] TASK-001", base_backlog)
        self.assertNotIn("[x] TASK-001", base_backlog)
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.tasks.integration.main_integrator.has_commits_ahead_of_branch", return_value=True)
    @patch("orc_core.tasks.integration.main_integrator.merge_task_branch_into_main")
    @patch("orc_core.tasks.execution.launch.cleanup_monitor_processes")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="process_exited")
    @patch("orc_core.notifications.notify.send_telegram_message")
    @patch("orc_core.tasks.execution.preflight._default_preflight")
    def test_fails_when_successful_integration_did_not_mark_base_backlog_done(self, mock_preflight, *_mocks) -> None:
        import orc_core.tasks.execution.engine as task_execution
        import orc_core.tasks.execution.finalize as task_execution_finalize

        mock_preflight.return_value = _fake_preflight(ok=True, error="")
        main_integrator.merge_task_branch_into_main.return_value = type(
            "Integration",
            (),
            {"ok": True, "conflict": False, "already_integrated": False, "error": ""},
        )()
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_dir = root / "base"
            worktree_dir = root / "worktree"
            base_dir.mkdir(parents=True, exist_ok=True)
            worktree_dir.mkdir(parents=True, exist_ok=True)
            request = _request(base_dir, worktree_dir)
            request = replace(request, integrate_to_main=True, main_branch="main")
            (worktree_dir / "BACKLOG.md").write_text("- [x] TASK-001 test task\n", encoding="utf-8")

            result = engine.execute(request)
            base_backlog = (base_dir / "BACKLOG.md").read_text(encoding="utf-8")

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "worktree_not_integrated_to_base")
        self.assertIn("[ ] TASK-001", base_backlog)
        self.assertEqual(worker.launch_calls, 1)


if __name__ == "__main__":
    unittest.main()
