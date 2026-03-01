#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import time
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core.supervisor_lifecycle import PROCESS_EXIT_GRACE_SECONDS, wait_for_completion, wait_for_process_exit


class _ExitedProc:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode

    def poll(self) -> int:
        return self.returncode


class _FakeMonitor:
    def __init__(self, *, workdir: str, returncode: int) -> None:
        self.proc = _ExitedProc(returncode)
        self.metrics = SimpleNamespace(
            total_lines=0,
            command_count=0,
            total_output_chars=0,
            tokens_total=0,
        )
        self.last_output_time = time.time()
        self.ui_followup_prompt = False
        self.workdir = workdir
        self.stderr_count = 0
        self.last_stderr_line = ""

    def maybe_report(self) -> None:
        return None

    def send_keys(self, *_args, **_kwargs) -> bool:
        return False


class SupervisorLifecycleTest(unittest.TestCase):
    def test_wait_for_completion_treats_missing_agent_pid_as_completed_when_backlog_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] REFACT-099 done\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-099","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=999999, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time()

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-099",
                task_text="repro",
            )

        self.assertEqual(result, "completed")

    def test_wait_for_completion_treats_missing_agent_pid_as_process_exited_when_not_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] REFACT-100 open\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-100","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=999999, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time()

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-100",
                task_text="repro",
            )

        self.assertEqual(result, "process_exited")

    def test_wait_for_completion_does_not_finish_only_from_done_backlog_while_agent_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] REFACT-005 done\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-005","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time() - 1000.0

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=600.0,
                task_ttl=0.2,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-005",
                task_text="repro",
            )

        self.assertEqual(result, "stalled")

    def test_wait_for_completion_treats_done_backlog_task_as_completed_after_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] REFACT-006 done\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-006","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)

            with patch("orc_core.supervisor_lifecycle.PROCESS_EXIT_GRACE_SECONDS", 0.01):
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=30.0,
                    task_ttl=30.0,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="REFACT-006",
                    task_text="repro",
                )

        self.assertEqual(result, "completed")

    def test_wait_for_completion_treats_exit_zero_with_active_task_as_process_exited(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-021",
                task_text="repro",
            )

        self.assertEqual(result, "process_exited")

    def test_wait_for_completion_waiting_for_input_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.ui_followup_prompt = True
            monitor.proc = SimpleNamespace(returncode=None, poll=lambda: None)

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-021",
                task_text="repro",
            )

        self.assertEqual(result, "waiting_for_input")

    def test_wait_for_completion_exit_zero_grace_window_allows_task_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)

            def _remove_task_file() -> None:
                time.sleep(0.05)
                if task_path.exists():
                    task_path.unlink()

            thread = threading.Thread(target=_remove_task_file)
            thread.start()
            started = time.time()
            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.05,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-021",
                task_text="repro",
            )
            thread.join(timeout=1.0)

        self.assertEqual(result, "completed")
        self.assertLess(time.time() - started, PROCESS_EXIT_GRACE_SECONDS + 1.0)

    def test_wait_for_completion_raises_on_confirmed_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)

            with self.assertRaises(KeyboardInterrupt):
                wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=30.0,
                    task_ttl=30.0,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="REFACT-021",
                    task_text="repro",
                    escape_requested=lambda: True,
                    confirm_exit=lambda: True,
                )

    def test_wait_for_process_exit_raises_on_confirmed_escape(self) -> None:
        monitor = _FakeMonitor(workdir=".", returncode=0)

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
