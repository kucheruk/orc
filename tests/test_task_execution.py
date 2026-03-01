#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import orc_core.task_execution as task_execution
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
    def _request(
        self,
        tmpdir: str,
        *,
        max_restarts: int = 2,
        commit_phase: bool = False,
        allow_fallback_commits: bool = False,
    ) -> TaskExecutionRequest:
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
            continue_template="continue {task_id} :: {reason}",
            commit_template="commit {task_id}",
            commit_phase=commit_phase,
            allow_fallback_commits=allow_fallback_commits,
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
            agent_output_log_path=None,
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
            retry_prompt = worker.launch_kwargs[1]["prompt_path"].read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 2)
        self.assertIn("Ты перестал выдавать результат", retry_prompt)

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
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    @patch("orc_core.task_execution.write_task_file")
    def test_missing_resume_id_fails_fast(self, write_task_file, *_mocks) -> None:
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

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "missing_conversation_id")
        self.assertEqual(worker.launch_calls, 0)
        write_task_file.assert_not_called()

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    @patch("orc_core.task_execution.write_task_file")
    def test_existing_task_file_with_other_backlog_starts_new_task(
        self,
        write_task_file,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            other_backlog = Path(tmpdir) / "OTHER_BACKLOG.md"
            other_backlog.write_text("- [ ] TASK-999 old\n", encoding="utf-8")
            request.task_path.write_text(
                '{"task_id":"TASK-999","task_text":"old task","backlog_path":"%s","conversation_id":"conv-1"}'
                % str(other_backlog),
                encoding="utf-8",
            )

            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)
        launch_kwargs = worker.launch_kwargs[0]
        self.assertIsNone(launch_kwargs["resume_id"])
        self.assertIsNone(launch_kwargs["resume_prompt"])
        write_task_file.assert_called_once()

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    def test_resume_flow_uses_reasoned_resume_prompt_on_restart(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["ttl_exceeded", "completed"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, max_restarts=2)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"conv-1"}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 2)
        self.assertEqual(worker.launch_kwargs[0]["resume_prompt"], "continue")
        self.assertIn("Ты превысил лимит времени", worker.launch_kwargs[1]["resume_prompt"])

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="waiting_for_input")
    def test_waiting_for_input_returns_continue_without_restart(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = TaskExecutionRequest(**{**request.__dict__, "nudge_cooldown": 7.0})
            result = engine.execute(request)

        self.assertEqual(result.status, "continue")
        self.assertEqual(result.reason, "waiting_for_input")
        self.assertEqual(result.delay_seconds, 7.0)
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.wait_for_process_exit", return_value="completed")
    @patch("orc_core.task_execution._git_status_porcelain")
    def test_commit_phase_fails_when_tracked_leftovers_and_fallback_disabled(
        self,
        git_status_mock,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        git_status_mock.side_effect = [
            (True, " M tracked.py\n"),
            (True, " M tracked.py\n"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=False)
            ok = task_execution._run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=task_execution.SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
            )

        self.assertFalse(ok)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.wait_for_process_exit", return_value="completed")
    @patch("orc_core.task_execution._attempt_autocommit_fallback", return_value=True)
    @patch("orc_core.task_execution._git_status_porcelain")
    def test_commit_phase_uses_fallback_when_enabled_and_succeeds(
        self,
        git_status_mock,
        fallback_mock,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        git_status_mock.side_effect = [
            (True, " M tracked.py\n"),
            (True, " M tracked.py\n"),
            (True, ""),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=True)
            ok = task_execution._run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=task_execution.SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
            )

        self.assertTrue(ok)
        fallback_mock.assert_called_once()

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.wait_for_process_exit", return_value="completed")
    @patch("orc_core.task_execution._attempt_autocommit_fallback", return_value=False)
    @patch("orc_core.task_execution._git_status_porcelain")
    def test_commit_phase_fails_when_enabled_fallback_fails(
        self,
        git_status_mock,
        fallback_mock,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        git_status_mock.side_effect = [
            (True, " M tracked.py\n"),
            (True, " M tracked.py\n"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=True)
            ok = task_execution._run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=task_execution.SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
            )

        self.assertFalse(ok)
        fallback_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
