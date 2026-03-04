#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
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

    def launch(self, **_kwargs):
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
        nudge_cooldown=1.0,
        nudge_text="continue",
        commit_stall_timeout=1.0,
        commit_ttl=1.0,
        progress_done=0,
        progress_total=1,
        agent_output_log_path=None,
    )


class TaskExecutionWorktreeStateTest(unittest.TestCase):
    @patch("orc_core.task_execution._cleanup_monitor_processes")
    @patch("orc_core.task_execution.wait_for_completion", return_value="waiting_for_input")
    @patch("orc_core.task_execution.send_telegram_message")
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

        self.assertEqual(send_telegram_message_mock.call_count, 1)
        start_message, _ = send_telegram_message_mock.call_args[0]
        self.assertIn("Старт задачи", start_message)

    @patch("orc_core.task_execution._cleanup_monitor_processes")
    @patch("orc_core.task_execution.wait_for_completion", return_value="stalled")
    @patch("orc_core.task_execution.send_telegram_message")
    def test_fails_fast_when_task_done_only_in_worktree_backlog(self, *_mocks) -> None:
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

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "worktree_not_integrated_to_base")
        self.assertEqual(worker.launch_calls, 1)


if __name__ == "__main__":
    unittest.main()
