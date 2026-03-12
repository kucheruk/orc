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
        self._watchdog_snapshot = {
            "count": 0,
            "oldest_age_seconds": 0.0,
            "oldest_label": "",
            "oldest_is_subagent": False,
        }

    def maybe_report(self) -> None:
        return None

    def send_keys(self, *_args, **_kwargs) -> bool:
        return False

    def active_tool_calls_watchdog_snapshot(self) -> dict:
        return dict(self._watchdog_snapshot)


class SupervisorLifecycleTest(unittest.TestCase):
    @patch("orc_core.supervisor_lifecycle.send_telegram_message")
    @patch("orc_core.supervisor_lifecycle._session_debug_log")
    @patch("orc_core.supervisor_lifecycle.time.sleep")
    def test_wait_for_completion_sends_stuck_notice_after_15m_without_token_changes(
        self,
        _sleep_mock,
        _session_debug_mock,
        send_telegram_message_mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(returncode=None, poll=lambda: None)
            monitor.metrics.tokens_total = 42
            monitor.last_output_time = 0.0

            report_calls = {"count": 0}

            def _maybe_report() -> None:
                report_calls["count"] += 1
                if report_calls["count"] >= 2:
                    monitor.ui_followup_prompt = True

            monitor.maybe_report = _maybe_report

            with patch(
                "orc_core.supervisor_lifecycle.time.time",
                side_effect=iter(
                    [
                        1000.0,  # start_time
                        1000.0,  # initial last_tokens_time
                        1000.1,  # loop#1 now
                        1000.2,  # maybe_report_started
                        1000.3,  # maybe_report_duration end
                        1000.4,  # last_tokens_time update on first token read
                        1000.5,  # stall check
                        1000.6,  # ttl check
                        1901.0,  # loop#2 now (>= 15m since last token update)
                        1901.1,  # maybe_report_started
                        1901.2,  # maybe_report_duration end
                        1901.3,  # since_tokens check
                        1901.4,  # cooldown check
                        1901.5,  # last_stuck_notice_time update
                    ]
                    + [1901.6] * 20
                ),
            ):
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=9999.0,
                    task_ttl=9999.0,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="PERSIST-001",
                    task_text="MongoDB Connection & Configuration",
                )

        self.assertEqual(result, "waiting_for_input")
        self.assertEqual(send_telegram_message_mock.call_count, 1)
        stuck_message, _ = send_telegram_message_mock.call_args[0]
        self.assertIn("tokens unchanged 15m", stuck_message)

    def test_wait_for_completion_treats_done_backlog_idle_agent_as_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] REFACT-777 done\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-777","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=None, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time() - 1000.0

            with patch("orc_core.supervisor_lifecycle.DONE_BACKLOG_IDLE_GRACE_SECONDS", 0.01):
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=600.0,
                    task_ttl=30.0,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="REFACT-777",
                    task_text="repro",
                )

        self.assertEqual(result, "completed")

    def test_wait_for_completion_ignores_preexisting_done_backlog_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [x] REFACT-778 done\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-778","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=None, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time() - 1000.0

            report_calls = {"count": 0}

            def _maybe_report() -> None:
                report_calls["count"] += 1
                monitor.ui_followup_prompt = True

            monitor.maybe_report = _maybe_report

            with patch("orc_core.supervisor_lifecycle.DONE_BACKLOG_IDLE_GRACE_SECONDS", 0.01):
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=600.0,
                    task_ttl=30.0,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="REFACT-778",
                    task_text="repro",
                    ignore_initial_backlog_done=True,
                )

        self.assertEqual(result, "waiting_for_input")
        self.assertGreaterEqual(report_calls["count"], 1)

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

            with patch("orc_core.supervisor_lifecycle.PID_MISSING_GRACE_SECONDS", 0.0):
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

            with patch("orc_core.supervisor_lifecycle.PID_MISSING_GRACE_SECONDS", 0.0):
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

    def test_wait_for_completion_does_not_force_close_tools_on_unconfirmed_pid_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            backlog_path = Path(tmpdir) / "BACKLOG.md"
            backlog_path.write_text("- [ ] REFACT-101 open\n", encoding="utf-8")
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text(
                '{"task_id":"REFACT-101","backlog_path":"%s"}' % str(backlog_path),
                encoding="utf-8",
            )
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=999999, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time()
            monitor.force_finalize_live_tool_calls = unittest.mock.MagicMock(
                return_value={"cleared": 1, "reason": "pid_missing", "pending": []}
            )

            with patch("orc_core.supervisor_lifecycle.PID_MISSING_GRACE_SECONDS", 0.0):
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
                    task_id="REFACT-101",
                    task_text="repro",
                )

        self.assertEqual(result, "process_exited")
        monitor.force_finalize_live_tool_calls.assert_not_called()

    def test_wait_for_completion_stalls_when_tool_digestion_exceeds_grace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=32101, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time() - 30.0
            monitor._watchdog_snapshot = {
                "count": 1,
                "oldest_age_seconds": 25.0,
                "oldest_label": "./scripts/ci/lint.sh && dotnet build",
                "oldest_is_subagent": False,
            }
            monitor.force_finalize_live_tool_calls = unittest.mock.MagicMock(
                return_value={"cleared": 1, "reason": "agent_digestion_timeout_5.0s", "pending": []}
            )

            with (
                patch("orc_core.supervisor_lifecycle._get_active_children_count", return_value=0),
                patch("orc_core.supervisor_lifecycle.TOOL_DIGESTION_GRACE_SECONDS", 5.0),
                patch("orc_core.supervisor_lifecycle.is_pid_alive", return_value=True),
            ):
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=600.0,
                    task_ttl=30.0,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="REFACT-102",
                    task_text="repro",
                )

        self.assertEqual(result, "stalled")
        monitor.force_finalize_live_tool_calls.assert_called_once()

    def test_wait_for_completion_ignores_stall_timeout_while_tool_child_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(pid=32102, returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time() - 30.0
            monitor._watchdog_snapshot = {
                "count": 1,
                "oldest_age_seconds": 25.0,
                "oldest_label": "./scripts/ci/lint.sh && dotnet build",
                "oldest_is_subagent": False,
            }
            monitor.force_finalize_live_tool_calls = unittest.mock.MagicMock(
                return_value={"cleared": 1, "reason": "tool_call_dispatch_stuck", "pending": []}
            )

            with (
                patch("orc_core.supervisor_lifecycle._get_active_children_count", return_value=1),
                patch("orc_core.supervisor_lifecycle.is_pid_alive", return_value=True),
            ):
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=monitor,
                    poll=0.01,
                    stall_timeout=0.01,
                    task_ttl=0.1,
                    log_path=Path(tmpdir) / "orc.log",
                    nudge_after=10,
                    nudge_cooldown=300.0,
                    nudge_text="continue",
                    task_id="REFACT-103",
                    task_text="repro",
                )

        self.assertEqual(result, "ttl_exceeded")
        monitor.force_finalize_live_tool_calls.assert_not_called()

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

            with patch("orc_core.supervisor_lifecycle.DONE_BACKLOG_IDLE_GRACE_SECONDS", 9999.0):
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

    def test_wait_for_completion_detects_model_unavailable_as_non_restartable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=1)
            monitor.stderr_count = 1
            monitor.last_stderr_line = "Cannot use this model: gpt-5.3-codex. Available models:"

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
                task_id="REFACT-104",
                task_text="repro",
            )

        self.assertEqual(result, "model_unavailable")

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

    @patch("orc_core.supervisor_lifecycle.timeline_instant")
    def test_wait_for_completion_emits_timeline_exit_reason(self, timeline_mock) -> None:
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
                timeline_id="tl-1",
                attempt=2,
            )

        self.assertEqual(result, "waiting_for_input")
        matching = [
            kwargs
            for _, kwargs in timeline_mock.call_args_list
            if kwargs.get("step") == "wait_for_completion_exit" and kwargs.get("result") == "waiting_for_input"
        ]
        self.assertTrue(matching)

    def test_wait_for_completion_ttl_counts_elapsed_before_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = Path(tmpdir) / "orc-task.json"
            task_path.write_text("{}", encoding="utf-8")
            monitor = _FakeMonitor(workdir=tmpdir, returncode=0)
            monitor.proc = SimpleNamespace(returncode=None, poll=lambda: None)
            monitor.last_output_time = time.time()

            result = wait_for_completion(
                task_path=task_path,
                monitor=monitor,
                poll=0.01,
                stall_timeout=30.0,
                task_ttl=1.0,
                elapsed_before_start=5.0,
                log_path=Path(tmpdir) / "orc.log",
                nudge_after=10,
                nudge_cooldown=300.0,
                nudge_text="continue",
                task_id="REFACT-021",
                task_text="repro",
            )

        self.assertEqual(result, "ttl_exceeded")

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
