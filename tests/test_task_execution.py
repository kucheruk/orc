#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import orc_core.tasks.execution.engine
import orc_core.tasks.execution.engine as task_execution
import orc_core.tasks.execution.finalize as task_execution_finalize
import orc_core.tasks.integration.main_integrator as main_integrator
import orc_core.tasks.execution.preflight as task_execution_preflight
from orc_core.git.git_helpers import classify_main_integration_error
from orc_core.git.task_adapters import SubprocessGitIntegration
from orc_core.tasks.ports import PreflightResult
from orc_core.tasks.stages.phases import run_commit_phase
from tests._fake_lifecycle import FakeLifecycle, FakeStatePaths, FakeStateWriter


def _fake_preflight(*, ok: bool, error: str):
    """Build a MainIntegrationPreflight stub that returns a PreflightResult."""
    result = PreflightResult(ok=ok, error=error)
    return SimpleNamespace(
        run=lambda **kwargs: result,
        classify_error=classify_main_integration_error,
    )
from orc_core.tasks.execution.engine import TaskExecutionEngine
from orc_core.tasks.execution.config import ModelConfig, TemplateConfig, TimingConfig
from orc_core.tasks.execution.request import TaskExecutionRequest
from orc_core.tasks.execution.stage import TaskStageSpec
from orc_core.text_parse import SafeDict
from orc_core.tasks.stages.artifacts import build_stage_artifact_bundle
from orc_core.tasks.dto import Task


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

    def build_snapshot(self):
        return SimpleNamespace(
            progress_done=4,
            progress_total=10,
            progress_remaining=6,
            eta_seconds=180.0,
        )

    def maybe_report(self): pass
    def refresh_process_status(self): return None
    def force_finalize_live_tool_calls(self, reason): return {}
    def active_tool_calls_watchdog_snapshot(self): return {}

class _FakeWorker:
    def __init__(self) -> None:
        self.launch_calls = 0
        self.launch_configs: list = []

    def launch(self, config):
        self.launch_calls += 1
        self.launch_configs.append(config)
        monitor = _FakeMonitor()
        monitor.workdir = str(getattr(config, "workdir", ""))
        return monitor


class _EmptySummaryMonitor(_FakeMonitor):
    def get_summary_text(self) -> str:
        return ""


class _EmptySummaryWorker(_FakeWorker):
    def launch(self, config):
        self.launch_calls += 1
        self.launch_configs.append(config)
        monitor = _EmptySummaryMonitor()
        monitor.workdir = str(getattr(config, "workdir", ""))
        return monitor


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
    def launch(self, config):
        self.launch_calls += 1
        self.launch_configs.append(config)
        monitor = _FragmentedSummaryMonitor()
        monitor.workdir = str(getattr(config, "workdir", ""))
        return monitor


class _FailingWorker:
    def launch(self, _config):
        raise TypeError("missing required keyword-only arguments: progress_done and progress_total")


class TaskExecutionEngineTest(unittest.TestCase):
    def _request(
        self,
        tmpdir: str,
        *,
        max_restarts: int = 2,
        commit_phase: bool = False,
        allow_fallback_commits: bool = False,
        stage_specs: tuple[TaskStageSpec, ...] = (),
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
            timing=TimingConfig(
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
            commit_phase=commit_phase,
            integrate_to_main=False,
            main_branch="main",
            allow_fallback_commits=allow_fallback_commits,
            progress_done=0,
            progress_total=1,
            enforce_stage_artifacts=bool(stage_specs),
            stage_specs=stage_specs,
            agent_output_log_path=None,
            process_lifecycle=FakeLifecycle(),
            state_writer=FakeStateWriter(),
            state_paths=FakeStatePaths(root),
        )

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_model_unavailable_fails_without_restart(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.return_value = "model_unavailable"
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, max_restarts=2))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "model_unavailable")
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_restart_loop_completes_on_second_attempt(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["stalled", "completed"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, max_restarts=2))
            retry_prompt = worker.launch_configs[1].prompt_path.read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 2)
        self.assertIn("Ты перестал выдавать результат", retry_prompt)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    def test_execute_emits_timeline_start_finish_pairs(
        self,
        _wait_for_completion,
        _write_task_file,
        _update_task_restart_count,
    ) -> None:
        original_timeline_step = orc_core.tasks.execution.stage_loop.timeline_step
        recorded_steps: list[str] = []

        @contextmanager
        def _tracking_timeline_step(**kwargs):
            recorded_steps.append(kwargs.get("step", ""))
            with original_timeline_step(**kwargs) as ts:
                yield ts

        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("orc_core.tasks.execution.engine.timeline_step", side_effect=_tracking_timeline_step), \
                 patch("orc_core.tasks.execution.stage_loop.timeline_step", side_effect=_tracking_timeline_step), \
                 patch("orc_core.tasks.execution.launch.timeline_step", side_effect=_tracking_timeline_step):
                result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertIn("task_execute", recorded_steps)
        self.assertIn("agent_attempt", recorded_steps)
        self.assertIn("wait_for_completion", recorded_steps)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
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

    @patch("orc_core.tasks.execution.finalize.run_commit_phase", return_value=True)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_done_task_on_stall_triggers_commit_phase(
        self,
        wait_for_completion,
        _write_task_file,
        _update_task_restart_count,
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

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_restart_loop_fails_after_max_restarts(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["stalled", "stalled"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, max_restarts=1))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "max_restarts_exceeded")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.tasks.execution.finalize.run_commit_phase", return_value=False)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    def test_commit_phase_failure_returns_failed_status(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, commit_phase=True))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "commit_phase_failed")

    @patch("orc_core.tasks.execution.finalize.is_quit_after_task_requested", return_value=True)
    @patch("orc_core.tasks.execution.finalize.run_commit_phase", return_value=True)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    def test_quit_after_task_forces_commit_phase_when_disabled(
        self,
        _wait_for_completion,
        _write_task_file,
        _update_task_restart_count,
        run_commit_phase,
        _is_quit_after_task_requested,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, commit_phase=False))

        self.assertEqual(result.status, "completed")
        self.assertTrue(result.committed)
        run_commit_phase.assert_called_once()

    @patch("orc_core.tasks.execution.finalize.is_quit_after_task_requested", return_value=True)
    @patch("orc_core.tasks.execution.finalize.run_commit_phase", return_value=False)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    def test_quit_after_task_forced_commit_failure_returns_failed_status(
        self,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir, commit_phase=False))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "commit_phase_failed")

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    def test_missing_resume_id_auto_drops_and_starts_fresh(self, write_task_file, *_mocks) -> None:
        """Missing conversation_id → auto-drop stale state → fresh start."""
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

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.resume.write_task_file")
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
        launch_configs = worker.launch_configs[0]
        self.assertIsNone(launch_configs.resume_id)
        self.assertIsNone(launch_configs.resume_prompt)
        write_task_file.assert_called_once()

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
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

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
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

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
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
        self.assertEqual(worker.launch_configs[0].resume_prompt, "continue")
        self.assertIn("Ты превысил лимит времени", worker.launch_configs[1].resume_prompt)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="waiting_for_input")
    def test_waiting_for_input_returns_continue_with_budget_tick(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = replace(request, timing=replace(request.timing, nudge_cooldown=7.0))
            result = engine.execute(request)

        self.assertEqual(result.status, "continue")
        self.assertEqual(result.reason, "waiting_for_input")
        self.assertEqual(result.delay_seconds, 7.0)
        self.assertEqual(worker.launch_calls, 1)

    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="waiting_for_input")
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

    @patch("orc_core.tasks.stages.phases.wait_for_process_exit", return_value="completed")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.status_porcelain")
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
            ok = run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
                timeline_id="tl-1",
                attempt=1,
            )

        self.assertFalse(ok)

    @patch("orc_core.tasks.stages.phases.wait_for_process_exit", return_value="completed")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.attempt_autocommit_fallback", return_value=True)
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.status_porcelain")
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
            ok = run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
                timeline_id="tl-1",
                attempt=1,
            )

        self.assertTrue(ok)
        fallback_mock.assert_called_once()

    @patch("orc_core.tasks.stages.phases.wait_for_process_exit", return_value="completed")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.attempt_autocommit_fallback", return_value=False)
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.status_porcelain")
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
            ok = run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
                timeline_id="tl-1",
                attempt=1,
            )

        self.assertFalse(ok)
        fallback_mock.assert_called_once()

    @patch("orc_core.tasks.stages.phases.wait_for_process_exit", return_value="completed")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.status_porcelain")
    def test_commit_phase_passes_progress_arguments_to_worker_launch(self, git_status_mock, *_mocks) -> None:
        worker = _FakeWorker()
        git_status_mock.side_effect = [(True, " M tracked.py\n"), (True, "")]

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=False)
            request = replace(request, progress_done=3, progress_total=9)
            ok = run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
                timeline_id="tl-1",
                attempt=1,
            )

        self.assertTrue(ok)
        self.assertEqual(worker.launch_calls, 1)
        self.assertEqual(worker.launch_configs[0].progress_done, 3)
        self.assertEqual(worker.launch_configs[0].progress_total, 9)

    @patch("orc_core.tasks.stages.phases.wait_for_process_exit", return_value="completed")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.status_porcelain")
    def test_commit_phase_ignores_runtime_artifact_leftovers(self, git_status_mock, *_mocks) -> None:
        worker = _FakeWorker()
        git_status_mock.side_effect = [
            (True, " M tracked.py\n"),
            (True, " M .orc/backlog-run/raw-stream/task.log\n?? .cursor/orc-task-runtime.json\n"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=False)
            ok = run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
                timeline_id="tl-1",
                attempt=1,
            )

        self.assertTrue(ok)

    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.status_porcelain", return_value=(True, " M tracked.py\n"))
    def test_commit_phase_launch_failure_returns_false_not_exception(self, *_mocks) -> None:
        worker = _FailingWorker()

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir, commit_phase=True, allow_fallback_commits=False)
            ok = run_commit_phase(
                worker=worker,
                request=request,
                prompt_vars=SafeDict(task_id="TASK-001", task_text="test task"),
                task_id="TASK-001",
                tag="tag",
                log_path=Path(tmpdir) / ".orc" / "orc.log",
                agent_output_log_path=str(Path(tmpdir) / ".orc" / "raw-stream.log"),
                timeline_id="tl-1",
                attempt=1,
            )

        self.assertFalse(ok)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    def test_execute_sets_default_agent_output_log_path_when_missing(self, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = engine.execute(self._request(tmpdir))

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 1)
        launch_path = worker.launch_configs[0].agent_output_log_path
        self.assertTrue(isinstance(launch_path, str) and launch_path.endswith(".log"))
        self.assertIn(".orc/run/raw-stream/", launch_path)

    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.merge_task_branch_into_main")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.has_commits_ahead_of_branch", return_value=False)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.preflight._default_preflight")
    def test_execute_skips_main_integration_when_worktree_not_ahead(self, mock_preflight, *_mocks) -> None:
        mock_preflight.return_value = _fake_preflight(ok=True, error="")
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = replace(request, integrate_to_main=True, main_branch="main")
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        SubprocessGitIntegration.merge_task_branch_into_main.assert_not_called()

    @patch("orc_core.tasks.integration.main_integrator.run_merge_expert_phase", return_value=True)
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.abort_merge")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.merge_task_branch_into_main")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.has_commits_ahead_of_branch", return_value=True)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.preflight._default_preflight")
    def test_execute_runs_merge_expert_when_main_integration_conflicts(
        self,
        mock_preflight,
        *_mocks,
    ) -> None:
        mock_preflight.return_value = _fake_preflight(ok=True, error="")
        SubprocessGitIntegration.merge_task_branch_into_main.side_effect = [
            SimpleNamespace(ok=False, conflict=True, error="conflict"),
            SimpleNamespace(ok=True, conflict=False, error=""),
        ]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = replace(request, integrate_to_main=True)
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(SubprocessGitIntegration.merge_task_branch_into_main.call_count, 2)
        main_integrator.run_merge_expert_phase.assert_called_once()

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.preflight._default_preflight")
    def test_execute_fails_fast_when_main_integration_preflight_fails(self, mock_preflight, *_mocks) -> None:
        mock_preflight.return_value = _fake_preflight(ok=False, error="base repository is dirty before integration: untracked:notes.txt")
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = replace(request, integrate_to_main=True)
            result = engine.execute(request)

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.reason,
            "main_integration_preflight_failed:dirty_base_repo:untracked:notes.txt",
        )
        self.assertEqual(worker.launch_calls, 0)

    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.merge_task_branch_into_main")
    @patch("orc_core.git.task_adapters.SubprocessGitIntegration.has_commits_ahead_of_branch", return_value=True)
    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    @patch("orc_core.tasks.execution.preflight._default_preflight")
    def test_execute_marks_specific_main_integration_failure_reason(
        self,
        mock_preflight,
        *_mocks,
    ) -> None:
        mock_preflight.return_value = _fake_preflight(ok=True, error="")
        SubprocessGitIntegration.merge_task_branch_into_main.return_value = SimpleNamespace(
            ok=False,
            conflict=False,
            error="checkout main failed: branch is locked",
        )

        original_timeline_step = orc_core.tasks.execution.stage_loop.timeline_step
        finished_records: list[dict] = []

        @contextmanager
        def _tracking_timeline_step(**kwargs):
            with original_timeline_step(**kwargs) as ts:
                yield ts
            finished_records.append({"step": kwargs.get("step"), "result": ts.result, "reason": ts.reason})

        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmpdir:
            request = self._request(tmpdir)
            request = replace(request, integrate_to_main=True)
            with patch("orc_core.tasks.execution.stage_loop.timeline_step", side_effect=_tracking_timeline_step), \
                 patch("orc_core.tasks.integration.main_integrator.timeline_step", side_effect=_tracking_timeline_step):
                result = engine.execute(request)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "main_integration_failed")
        reasons = [
            rec["reason"]
            for rec in finished_records
            if rec["step"] == "main_integration"
        ]
        self.assertIn("main_integration_failed:checkout_failed", reasons)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_runs_sdlc_stages_in_order_with_fresh_runs(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["completed"] * 6
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="planning", model="model-a", prompt_template="planning {task_id}"),
            TaskStageSpec(stage_id="design", model="model-b", prompt_template="design {task_id}"),
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
            TaskStageSpec(stage_id="review", model="model-d", prompt_template="review {task_id}"),
            TaskStageSpec(stage_id="testing", model="model-e", prompt_template="testing {task_id}"),
            TaskStageSpec(stage_id="handoff", model="model-f", prompt_template="handoff {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            artifact_bundle.plan.write_text("plan", encoding="utf-8")
            artifact_bundle.design.write_text("design", encoding="utf-8")
            artifact_bundle.implementation.write_text("implementation", encoding="utf-8")
            artifact_bundle.review.write_text("status: approved\nreview", encoding="utf-8")
            artifact_bundle.testing.write_text("status: pass\ntesting", encoding="utf-8")
            artifact_bundle.handoff.write_text("handoff", encoding="utf-8")
            result = engine.execute(self._request(tmpdir, stage_specs=stages))
            prompt_payloads = [
                Path(call.prompt_path).read_text(encoding="utf-8")
                for call in worker.launch_configs
            ]

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 6)
        self.assertEqual([call.model for call in worker.launch_configs], [stage.model for stage in stages])
        self.assertTrue(all(call.resume_id is None for call in worker.launch_configs))
        self.assertTrue(all(call.resume_prompt is None for call in worker.launch_configs))
        self.assertEqual(
            prompt_payloads,
            [
                "planning TASK-001",
                "design TASK-001",
                "impl TASK-001",
                "review TASK-001",
                "testing TASK-001",
                "handoff TASK-001",
            ],
        )

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_stops_sdlc_pipeline_when_middle_stage_fails(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["completed", "model_unavailable"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="planning", model="model-a", prompt_template="planning {task_id}"),
            TaskStageSpec(stage_id="design", model="model-b", prompt_template="design {task_id}"),
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            artifact_bundle.plan.write_text("plan", encoding="utf-8")
            result = engine.execute(self._request(tmpdir, stage_specs=stages))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "model_unavailable")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_fails_when_sdlc_stage_artifact_missing(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.side_effect = ["completed", "completed"]
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="planning", model="model-a", prompt_template="planning {task_id}"),
            TaskStageSpec(stage_id="design", model="model-b", prompt_template="design {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            artifact_bundle.plan.write_text("plan", encoding="utf-8")
            result = engine.execute(self._request(tmpdir, stage_specs=stages))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "stage_artifact_design_missing")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_feedback_loop_returns_to_implementation_before_testing(self, wait_for_completion, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
            TaskStageSpec(stage_id="review", model="model-d", prompt_template="review {task_id}"),
            TaskStageSpec(stage_id="testing", model="model-e", prompt_template="testing {task_id}"),
            TaskStageSpec(stage_id="handoff", model="model-f", prompt_template="handoff {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            stage_counter = {"count": 0}

            def _write_stage_artifacts(*_args, **_kwargs):
                stage_counter["count"] += 1
                index = stage_counter["count"]
                if index in (1, 3):
                    artifact_bundle.implementation.write_text(f"implementation-{index}", encoding="utf-8")
                elif index == 2:
                    artifact_bundle.review.write_text("status: needs_changes\nfix required", encoding="utf-8")
                elif index == 4:
                    artifact_bundle.review.write_text("status: approved\nready for testing", encoding="utf-8")
                elif index == 5:
                    artifact_bundle.testing.write_text("status: pass\nall checks green", encoding="utf-8")
                elif index == 6:
                    artifact_bundle.handoff.write_text("handoff", encoding="utf-8")
                return "completed"

            wait_for_completion.side_effect = _write_stage_artifacts
            result = engine.execute(self._request(tmpdir, stage_specs=stages))
            prompt_payloads = [Path(call.prompt_path).read_text(encoding="utf-8") for call in worker.launch_configs]

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 6)
        self.assertEqual(
            prompt_payloads,
            [
                "impl TASK-001",
                "review TASK-001",
                "impl TASK-001",
                "review TASK-001",
                "testing TASK-001",
                "handoff TASK-001",
            ],
        )

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_feedback_loop_fails_after_iteration_limit(self, wait_for_completion, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
            TaskStageSpec(stage_id="review", model="model-d", prompt_template="review {task_id}"),
            TaskStageSpec(stage_id="testing", model="model-e", prompt_template="testing {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            stage_counter = {"count": 0}

            def _write_stage_artifacts(*_args, **_kwargs):
                stage_counter["count"] += 1
                index = stage_counter["count"]
                if index % 2 == 1:
                    artifact_bundle.implementation.write_text(f"implementation-{index}", encoding="utf-8")
                else:
                    artifact_bundle.review.write_text("status: needs_changes\nstill broken", encoding="utf-8")
                return "completed"

            wait_for_completion.side_effect = _write_stage_artifacts
            result = engine.execute(self._request(tmpdir, stage_specs=stages))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "sdlc_feedback_limit_exceeded")
        self.assertEqual(worker.launch_calls, 8)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_retries_when_process_exits_after_backlog_done_without_artifact(
        self,
        wait_for_completion,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")

            def _write_stage_artifacts(*_args, **_kwargs):
                if len(worker.launch_configs) == 1:
                    Path(tmpdir, "BACKLOG.md").write_text("- [x] TASK-001 test task\n", encoding="utf-8")
                    return "process_exited"
                artifact_bundle.implementation.write_text("implementation", encoding="utf-8")
                return "completed"

            wait_for_completion.side_effect = _write_stage_artifacts
            result = engine.execute(self._request(tmpdir, stage_specs=stages))

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_fails_with_missing_artifact_after_single_retry_budget(
        self,
        wait_for_completion,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            def _always_exit_without_artifact(*_args, **_kwargs):
                Path(tmpdir, "BACKLOG.md").write_text("- [x] TASK-001 test task\n", encoding="utf-8")
                return "process_exited"

            wait_for_completion.side_effect = _always_exit_without_artifact
            result = engine.execute(self._request(tmpdir, stage_specs=stages, max_restarts=5))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "stage_artifact_implementation_missing")
        self.assertEqual(worker.launch_calls, 2)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_continues_to_handoff_when_implementation_marks_task_done_before_final_stage(
        self,
        wait_for_completion,
        *_mocks,
    ) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
            TaskStageSpec(stage_id="handoff", model="model-h", prompt_template="handoff {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")

            def _write_stage_artifacts(*_args, **_kwargs):
                if len(worker.launch_configs) == 1:
                    artifact_bundle.implementation.write_text("implementation", encoding="utf-8")
                    Path(tmpdir, "BACKLOG.md").write_text("- [x] TASK-001 test task\n", encoding="utf-8")
                    return "process_exited"
                artifact_bundle.handoff.write_text("handoff", encoding="utf-8")
                return "completed"

            wait_for_completion.side_effect = _write_stage_artifacts
            result = engine.execute(self._request(tmpdir, stage_specs=stages))
            prompt_payloads = [Path(call.prompt_path).read_text(encoding="utf-8") for call in worker.launch_configs]

        self.assertEqual(result.status, "completed")
        self.assertEqual(worker.launch_calls, 2)
        self.assertEqual(
            prompt_payloads,
            [
                "impl TASK-001",
                "handoff TASK-001",
            ],
        )
        self.assertFalse(wait_for_completion.call_args_list[0].kwargs["ignore_initial_backlog_done"])
        self.assertTrue(wait_for_completion.call_args_list[1].kwargs["ignore_initial_backlog_done"])

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_fails_when_testing_verdict_is_fail(self, wait_for_completion, *_mocks) -> None:
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(stage_id="implementation", model="model-c", prompt_template="impl {task_id}"),
            TaskStageSpec(stage_id="review", model="model-d", prompt_template="review {task_id}"),
            TaskStageSpec(stage_id="testing", model="model-e", prompt_template="testing {task_id}"),
            TaskStageSpec(stage_id="handoff", model="model-f", prompt_template="handoff {task_id}"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            stage_counter = {"count": 0}

            def _write_stage_artifacts(*_args, **_kwargs):
                stage_counter["count"] += 1
                index = stage_counter["count"]
                if index == 1:
                    artifact_bundle.implementation.write_text("implementation", encoding="utf-8")
                elif index == 2:
                    artifact_bundle.review.write_text("status: approved\nok", encoding="utf-8")
                elif index == 3:
                    artifact_bundle.testing.write_text("status: fail\ntests are red", encoding="utf-8")
                return "completed"

            wait_for_completion.side_effect = _write_stage_artifacts
            result = engine.execute(self._request(tmpdir, stage_specs=stages))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "testing_failed")
        self.assertEqual(worker.launch_calls, 3)

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion")
    def test_execute_injects_stage_artifact_prompt_variables(self, wait_for_completion, *_mocks) -> None:
        wait_for_completion.return_value = "completed"
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))
        stages = (
            TaskStageSpec(
                stage_id="planning",
                model="model-a",
                prompt_template=(
                    "artifacts={artifacts_dir}\n"
                    "plan={artifact_plan}\n"
                    "design={artifact_design}\n"
                    "impl={artifact_implementation}\n"
                    "review={artifact_review}\n"
                    "testing={artifact_testing}\n"
                    "handoff={artifact_handoff}"
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_bundle = build_stage_artifact_bundle(workdir=tmpdir, task_id="TASK-001")
            artifact_bundle.plan.write_text("plan", encoding="utf-8")
            result = engine.execute(self._request(tmpdir, stage_specs=stages))
            prompt_payload = Path(worker.launch_configs[0].prompt_path).read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed")
        self.assertIn(f"artifacts={artifact_bundle.artifacts_dir}", prompt_payload)
        self.assertIn(f"plan={artifact_bundle.plan}", prompt_payload)
        self.assertIn(f"design={artifact_bundle.design}", prompt_payload)
        self.assertIn(f"impl={artifact_bundle.implementation}", prompt_payload)
        self.assertIn(f"review={artifact_bundle.review}", prompt_payload)
        self.assertIn(f"testing={artifact_bundle.testing}", prompt_payload)
        self.assertIn(f"handoff={artifact_bundle.handoff}", prompt_payload)


if __name__ == "__main__":
    unittest.main()
