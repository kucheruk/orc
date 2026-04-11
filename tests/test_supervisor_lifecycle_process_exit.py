#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from orc_core.supervisor_lifecycle import wait_for_process_exit


class _FakeMonitor:
    def __init__(self) -> None:
        self.proc = SimpleNamespace(pid=999999, returncode=None, poll=lambda: None)
        self.last_output_time = time.time()
        self.ui_followup_prompt = False
        self.process_group_id = None
        self.started_at = 0.0
        self.run_token = ""
        self.result_status = None
        self.stderr_count = 0
        self.last_stderr_line = ""

    def maybe_report(self) -> None:
        return None


    def stop(self): pass
    def get_summary_text(self): return ""
    def refresh_process_status(self): return None
    def force_finalize_live_tool_calls(self, reason): return {}
    def active_tool_calls_watchdog_snapshot(self): return {}

class _BrokenMonitor(_FakeMonitor):

    def maybe_report(self) -> None:
        raise RuntimeError("monitor boom")


class WaitForProcessExitPidMissingTest(unittest.TestCase):
    def test_wait_for_process_exit_returns_process_exited_when_pid_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = wait_for_process_exit(
                monitor=_FakeMonitor(),
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=Path(tmpdir) / "orc.log",
                label="commit_phase",
                stop_on_followup_prompt=True,
            )
        self.assertEqual(result, "process_exited")

    def test_wait_for_process_exit_returns_process_exited_when_maybe_report_crashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            result = wait_for_process_exit(
                monitor=_BrokenMonitor(),
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=30.0,
                log_path=log_path,
                label="commit_phase",
                stop_on_followup_prompt=True,
            )
            self.assertEqual(result, "process_exited")
            lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertTrue(lines)
            self.assertIn("phase monitor maybe_report crashed", lines[-1])


if __name__ == "__main__":
    unittest.main()

