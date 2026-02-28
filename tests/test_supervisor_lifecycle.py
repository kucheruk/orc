#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core.supervisor_lifecycle import wait_for_completion, wait_for_process_exit


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
    @patch("orc_core.supervisor_lifecycle.hard_cleanup_after_success", return_value=False)
    @patch("orc_core.supervisor_lifecycle.invoke_stop_hook_fallback")
    def test_wait_for_completion_treats_exit_zero_as_completed_after_cleanup(
        self, invoke_stop_hook_fallback, hard_cleanup_after_success
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            
            def _fallback(_workdir: str, _task_path: Path, _log_path: Path) -> bool:
                task_path.unlink()
                return True

            invoke_stop_hook_fallback.side_effect = _fallback

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

        self.assertEqual(result, "completed")
        invoke_stop_hook_fallback.assert_called_once()
        hard_cleanup_after_success.assert_not_called()

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
