#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from orc_core.tasks.dto import Task
from orc_core.tasks.execution.attempt_env import build_attempt_agent_env
from orc_core.tasks.execution.config import ModelConfig, TemplateConfig, TimingConfig
from orc_core.tasks.execution.engine import TaskExecutionEngine
from orc_core.tasks.execution.request import TaskExecutionRequest
from tests._fake_lifecycle import FakeLifecycle, FakeStatePaths, FakeStateWriter


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
        return None

    def maybe_report(self):
        return None

    def refresh_process_status(self):
        return None

    def force_finalize_live_tool_calls(self, _reason):
        return {}

    def active_tool_calls_watchdog_snapshot(self):
        return {}


class _FakeWorker:
    def __init__(self) -> None:
        self.launch_configs: list = []

    def launch(self, config):
        self.launch_configs.append(config)
        monitor = _FakeMonitor()
        monitor.workdir = str(config.workdir)
        return monitor


class AttemptAgentEnvTest(unittest.TestCase):
    def test_build_attempt_agent_env_uses_result_tag_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = build_attempt_agent_env(
                {"BASE": "1", "ORC_AGENT_RESULT_TAG": "review-pass"},
                run_root=Path(tmp) / "run",
                task_id="TASK-7",
                stage_id="implementation",
                attempt=2,
            )
        self.assertEqual(env["BASE"], "1")
        self.assertEqual(env["ORC_AGENT_RUN_ID"], "TASK-7:review-pass:attempt-2")
        self.assertTrue(env["ORC_AGENT_RESULT_FILE"].endswith("TASK-7__review-pass__attempt-2.json"))

    @patch("orc_core.tasks.execution.stage_loop.update_task_restart_count")
    @patch("orc_core.tasks.execution.resume.write_task_file")
    @patch("orc_core.tasks.execution.launch.wait_for_completion", return_value="completed")
    def test_engine_injects_result_env_per_attempt(self, *_mocks):
        worker = _FakeWorker()
        engine = TaskExecutionEngine(worker=worker, log_path=Path("/tmp/orc.log"))

        with tempfile.TemporaryDirectory() as tmp:
            request = _request(tmp)
            request = replace(request, agent_env={"ORC_AGENT_RESULT_TAG": "coding-pass"})
            result = engine.execute(request)

        self.assertEqual(result.status, "completed")
        launch_env = worker.launch_configs[0].agent_env
        self.assertEqual(launch_env["ORC_AGENT_RUN_ID"], "TASK-001:coding-pass:attempt-1")
        self.assertTrue(launch_env["ORC_AGENT_RESULT_FILE"].endswith("TASK-001__coding-pass__attempt-1.json"))


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
            stall_timeout=60.0,
            task_ttl=60.0,
            max_restarts=0,
            report_interval=15.0,
            summary_lines=25,
            nudge_after=0.0,
            nudge_cooldown=0.0,
            nudge_text="",
            commit_stall_timeout=60.0,
            commit_ttl=60.0,
        ),
        models=ModelConfig(model="test-model", commit_model="test-model", merge_expert_model="test-model"),
        templates=TemplateConfig(prompt_template="{task_text}", continue_template="", commit_template="", merge_expert_template=""),
        commit_phase=False,
        integrate_to_main=False,
        main_branch="main",
        allow_fallback_commits=False,
        progress_done=0,
        progress_total=1,
        state_writer=FakeStateWriter(),
        state_paths=FakeStatePaths(root),
        process_lifecycle=FakeLifecycle(),
    )


if __name__ == "__main__":
    unittest.main()
