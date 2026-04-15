#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.tasks.completion.lifecycle import wait_for_completion, wait_for_process_exit
from orc_core.tasks.completion.ports import NoopNotify
from orc_core.tasks.backlog_query import MarkdownBacklogQuery


class _FakeMetrics:
    total_lines = 0
    command_count = 0
    total_output_chars = 0
    tokens_total = None


class _FakeProc:
    def __init__(self, *, poll_values: list[int | None]) -> None:
        self._poll_values = poll_values
        self.returncode = 0

    def poll(self):
        if self._poll_values:
            value = self._poll_values.pop(0)
            if value is not None:
                self.returncode = value
            return value
        return 0


class _FakeMonitor:
    def __init__(self, *, poll_values: list[int | None]) -> None:
        self.proc = _FakeProc(poll_values=poll_values)
        self.metrics = _FakeMetrics()
        self.last_output_time = 10**9
        self.ui_followup_prompt = False
        self.result_status = None
        self.result_seen_at = None
        self.workdir = "."
        self.stderr_count = 0
        self.last_stderr_line = ""
        self.process_group_id = None
        self.started_at = 0.0
        self.run_token = ""
        self.result_status = None
        self.stderr_count = 0
        self.last_stderr_line = ""

    def maybe_report(self) -> None:
        return None

    def send_keys(self, *_args, **_kwargs) -> bool:
        return False


    def stop(self): pass
    def get_summary_text(self): return ""
    def refresh_process_status(self): return None
    def force_finalize_live_tool_calls(self, reason): return {}
    def active_tool_calls_watchdog_snapshot(self): return {}

class SupervisorEscapeTest(unittest.TestCase):

    def test_wait_for_completion_raises_on_confirmed_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(poll_values=[None])

            with self.assertRaises(KeyboardInterrupt):
                wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=10.0,
                    task_ttl=10.0,
                    log_path=Path("/tmp/orc.log"),
                    nudge_after=10,
                    nudge_cooldown=60.0,
                    nudge_text="continue",
                    task_id="TASK-001",
                    task_text="test",
                    notify=NoopNotify(),
                    backlog_query=MarkdownBacklogQuery(),
                    escape_requested=lambda: True,
                    confirm_exit=lambda: True,
                )

    def test_wait_for_completion_keeps_running_when_escape_not_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(poll_values=[0])
            calls = {"count": 0}

            def escape_requested() -> bool:
                calls["count"] += 1
                return calls["count"] == 1

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=10.0,
                task_ttl=10.0,
                log_path=Path("/tmp/orc.log"),
                nudge_after=10,
                nudge_cooldown=60.0,
                nudge_text="continue",
                task_id="TASK-001",
                task_text="test",
                notify=NoopNotify(),
                backlog_query=MarkdownBacklogQuery(),
                escape_requested=escape_requested,
                confirm_exit=lambda: False,
            )

            self.assertEqual(result, "process_exited")

    def test_wait_for_process_exit_raises_on_confirmed_escape(self) -> None:
        monitor = _FakeMonitor(poll_values=[None])

        with self.assertRaises(KeyboardInterrupt):
            wait_for_process_exit(
                monitor=monitor,
                poll=0.01,
                stall_timeout=10.0,
                task_ttl=10.0,
                log_path=Path("/tmp/orc.log"),
                label="commit_phase",
                stop_on_followup_prompt=True,
                escape_requested=lambda: True,
                confirm_exit=lambda: True,
            )


if __name__ == "__main__":
    unittest.main()
