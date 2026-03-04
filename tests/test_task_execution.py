#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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


class _EmptySummaryMonitor(_FakeMonitor):
    def get_summary_text(self) -> str:
        return ""


class _EmptySummaryWorker(_FakeWorker):
    def launch(self, **kwargs):
        self.launch_calls += 1
        self.launch_kwargs.append(kwargs)
        return _EmptySummaryMonitor()


class _FragmentedSummaryMonitor(_FakeMonitor):
    def get_summary_text(self) -> str:
        return "\n".join(
            [
                "ента",
                "(",
                "build",
                "/test",
                "/",
                "compose",
                "/header",
                "-check",
                "),",
                "после",
                "чего",
                "доб",
                "ью",
                "остав",
                "шиеся",
                "замеч",
                "ания",
                ",",
                "если",
                "что",
                "-то",
                "не",
                "пройдет",
                ".",
            ]
        )


class _FragmentedSummaryWorker(_FakeWorker):
    def launch(self, **kwargs):
        self.launch_calls += 1
        self.launch_kwargs.append(kwargs)
        return _FragmentedSummaryMonitor()


class _FailingWorker:
    def launch(self, **_kwargs):
        raise TypeError("missing required keyword-only arguments: progress_done and progress_total")


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
            base_workdir=tmpdir,
            run_root=root / ".orc" / "run",
            model="gpt-5.2-codex",
            commit_model="gpt-5.2-codex",
            merge_expert_model="gpt-5.2-codex",
            prompt_template="{task_id} {task_text}",
            continue_template="continue {task_id} :: {reason}",
            commit_template="commit {task_id}",
            merge_expert_template="merge {task_id}",
            commit_phase=commit_phase,
            integrate_to_main=False,
            main_branch="main",
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
    @patch("orc_core.task_execution.send_telegram_message")
    def test_completed_sends_telegram_summary_when_present(self, send_telegram_message_mock, wait_for_completion, *_mocks) -> None:
        wait_for_completion.return_value = "completed"
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertEqual(send_telegram_message_mock.call_count, 2)
        start_message, _ = send_telegram_message_mock.call_args_list[0][0]
        finish_message, _ = send_telegram_message_mock.call_args_list[1][0]
        self.assertIn("Старт задачи", start_message)
        self.assertIn("Задача завершена", finish_message)
        self.assertIn("TASK-001", finish_message)
        self.assertIn("done", finish_message)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    @patch("orc_core.task_execution.send_telegram_message")
    def test_completed_skips_telegram_summary_when_empty(self, send_telegram_message_mock, wait_for_completion, *_mocks) -> None:
        wait_for_completion.return_value = "completed"
        worker = _EmptySummaryWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertEqual(send_telegram_message_mock.call_count, 2)
        start_message, _ = send_telegram_message_mock.call_args_list[0][0]
        finish_message, _ = send_telegram_message_mock.call_args_list[1][0]
        self.assertIn("Старт задачи", start_message)
        self.assertIn("Задача завершена", finish_message)
        self.assertIn("Отчёт отсутствует", finish_message)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    @patch("orc_core.task_execution.send_telegram_message")
    def test_completed_uses_task_report_markdown_as_message_body(self, send_telegram_message_mock, wait_for_completion, *_mocks) -> None:
        wait_for_completion.return_value = "completed"
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            task_report_dir = Path(tmpdir) / "tasks"
            task_report_dir.mkdir(parents=True, exist_ok=True)
            (task_report_dir / "TASK-001.md").write_text("Готово.\n\nПроверки выполнены.", encoding="utf-8")
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertEqual(send_telegram_message_mock.call_count, 2)
        finish_message, _ = send_telegram_message_mock.call_args_list[1][0]
        self.assertIn("Задача завершена: TASK-001", finish_message)
        self.assertIn("Готово.", finish_message)
        self.assertNotIn("\n\ndone", finish_message)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    @patch("orc_core.task_execution.send_telegram_message")
    def test_completed_normalizes_fragmented_fallback_summary(self, send_telegram_message_mock, wait_for_completion, *_mocks) -> None:
        wait_for_completion.return_value = "completed"
        worker = _FragmentedSummaryWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertEqual(send_telegram_message_mock.call_count, 2)
        finish_message, _ = send_telegram_message_mock.call_args_list[1][0]
        self.assertIn("build/test/compose/header-check", finish_message)
        self.assertIn("доб ью", finish_message)
        self.assertIn("что-то", finish_message)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="waiting_for_input")
    @patch("orc_core.task_execution.send_telegram_message")
    def test_start_notification_sent_for_fresh_task_only(self, send_telegram_message_mock, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "continue")
        self.assertEqual(send_telegram_message_mock.call_count, 1)
        start_message, _ = send_telegram_message_mock.call_args[0]
        self.assertIn("Старт задачи", start_message)

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
    def test_done_task_on_stall_finishes_without_restart(self, wait_for_completion, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, max_restarts=2)

            def _mark_done_then_stall(*_args, **_kwargs):
                request.backlog_path.write_text("- [x] TASK-001 test task\n", encoding="utf-8")
                return "stalled"

            wait_for_completion.side_effect = _mark_done_then_stall
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"conv-1"}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.task_execution._run_commit_phase", return_value=True)
    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion")
    def test_done_task_on_stall_triggers_commit_phase(
        self,
        wait_for_completion,
        _write_task_file,
        _update_task_restart_count,
        _kill_process_tree,
        run_commit_phase,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, max_restarts=2, commit_phase=True)

            def _mark_done_then_stall(*_args, **_kwargs):
                request.backlog_path.write_text("- [x] TASK-001 test task\n", encoding="utf-8")
                return "stalled"

            wait_for_completion.side_effect = _mark_done_then_stall
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"conv-1"}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)
        run_commit_phase.assert_called_once()

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
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    def test_existing_task_file_with_other_backlog_resets_elapsed_baseline(
        self,
        wait_for_completion,
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
            request.task_path.with_name("orc-task-runtime.json").write_text(
                '{"version":1,"task_id":"TASK-999","active_seconds":999.0,"last_heartbeat_at":0.0,"run_id":""}',
                encoding="utf-8",
            )

            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(wait_for_completion.call_args.kwargs.get("elapsed_before_start"), 0.0)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    def test_resume_elapsed_baseline_reads_runtime_state(
        self,
        wait_for_completion,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"conv-1"}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            request.task_path.with_name("orc-task-runtime.json").write_text(
                '{"version":1,"task_id":"TASK-001","active_seconds":42.5,"last_heartbeat_at":0.0,"run_id":""}',
                encoding="utf-8",
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(wait_for_completion.call_args.kwargs.get("elapsed_before_start"), 42.5)

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
    def test_waiting_for_input_returns_continue_with_budget_tick(self, *_mocks) -> None:
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
    @patch("orc_core.task_execution.wait_for_completion", return_value="waiting_for_input")
    @patch("orc_core.task_execution.send_telegram_message")
    def test_waiting_for_input_resume_restores_restart_count_and_fails_on_budget(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, max_restarts=1)
            request.task_path.parent.mkdir(parents=True, exist_ok=True)
            request.task_path.write_text(
                '{"task_id":"TASK-001","task_text":"test task","backlog_path":"%s","conversation_id":"conv-1","restart_count":1}'
                % str(request.backlog_path),
                encoding="utf-8",
            )
            result = engine.execute(request)
            state_after = json.loads(request.task_path.read_text(encoding="utf-8"))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "max_restarts_exceeded")
        self.assertEqual(worker.launch_calls, 1)
        self.assertEqual(int(state_after.get("restart_count", -1)), 2)

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
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
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
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
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
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
            )

        self.assertFalse(ok)
        fallback_mock.assert_called_once()

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.wait_for_process_exit", return_value="completed")
    @patch("orc_core.task_execution._git_status_porcelain")
    def test_commit_phase_passes_progress_arguments_to_worker_launch(self, git_status_mock, *_mocks) -> None:
        worker = _FakeWorker()
        git_status_mock.side_effect = [(True, " M tracked.py\n"), (True, "")]

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=False)
            request = TaskExecutionRequest(**{**request.__dict__, "progress_done": 3, "progress_total": 9})
            ok = task_execution._run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=task_execution.SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
            )

        self.assertTrue(ok)
        self.assertEqual(worker.launch_calls, 1)
        self.assertEqual(worker.launch_kwargs[0]["progress_done"], 3)
        self.assertEqual(worker.launch_kwargs[0]["progress_total"], 9)

    @patch("orc_core.task_execution._git_status_porcelain", return_value=(True, " M tracked.py\n"))
    def test_commit_phase_launch_failure_returns_false_not_exception(self, *_mocks) -> None:
        worker = _FailingWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=False)
            ok = task_execution._run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=task_execution.SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
            )

        self.assertFalse(ok)

    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    def test_execute_sets_default_agent_output_log_path_when_missing(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)
        launch_path = worker.launch_kwargs[0]["agent_output_log_path"]
        self.assertTrue(isinstance(launch_path, str) and launch_path.endswith(".log"))
        self.assertIn(".orc/run/raw-stream/", launch_path)

    @patch("orc_core.task_execution.integrate_commit_into_main")
    @patch("orc_core.task_execution._has_commits_ahead_of_branch", return_value=False)
    @patch("orc_core.task_execution.get_head_commit", return_value="abc123")
    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    def test_execute_skips_main_integration_when_worktree_not_ahead(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = TaskExecutionRequest(
                **{**request.__dict__, "integrate_to_main": True, "main_branch": "main"}
            )
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        task_execution.integrate_commit_into_main.assert_not_called()

    @patch("orc_core.task_execution._run_merge_expert_phase", return_value=True)
    @patch("orc_core.task_execution.integrate_commit_into_main")
    @patch("orc_core.task_execution._has_commits_ahead_of_branch", return_value=True)
    @patch("orc_core.task_execution.get_head_commit", return_value="abc123")
    @patch("orc_core.task_execution.kill_process_tree")
    @patch("orc_core.task_execution.update_task_restart_count")
    @patch("orc_core.task_execution.write_task_file")
    @patch("orc_core.task_execution.wait_for_completion", return_value="completed")
    def test_execute_runs_merge_expert_when_main_integration_conflicts(
        self,
        *_mocks,
    ) -> None:
        task_execution.integrate_commit_into_main.side_effect = [
            SimpleNamespace(ok=False, conflict=True, error="conflict"),
            SimpleNamespace(ok=True, conflict=False, error=""),
        ]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = TaskExecutionRequest(**{**request.__dict__, "integrate_to_main": True})
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(task_execution.integrate_commit_into_main.call_count, 2)
        task_execution._run_merge_expert_phase.assert_called_once()


if __name__ == "__main__":
    unittest.main()
