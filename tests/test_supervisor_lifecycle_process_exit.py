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

    def maybe_report(self) -> None:
        return None


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


if __name__ == "__main__":
    unittest.main()

