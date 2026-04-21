#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import io
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import orc_core.errors.crash_handler as crash_handler_module
import orc_core.infra.io.logging as logging_module
from orc_core.errors.crash_handler import (
    build_crash_stdout_payload,
    emit_crash_stdout_payload,
    install_crash_handlers,
    report_fatal_exception,
)
from orc_core.infra.io.debug_log import init_debug_logging
from orc_core.log import log_event, set_log_context
from orc_core.infra.io.timeline import (
    timeline_instant,
    timeline_step,
    timeline_step_finished,
    timeline_step_started,
)


class LoggingContextTest(unittest.TestCase):
    def tearDown(self) -> None:
        set_log_context(workdir="")

    def test_log_event_includes_workspace_and_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict("os.environ", {"ORC_LOG_LEVEL": "DEBUG"}, clear=False):
            log_path = Path(tmpdir) / "orc.log"
            workspace = Path(tmpdir) / "project"
            workspace.mkdir(parents=True, exist_ok=True)

            set_log_context(workdir=str(workspace))
            log_event(log_path, "INFO", "event with context", task_id="TASK-1")

            payload = json.loads(log_path.read_text(encoding="utf-8").strip())

        self.assertEqual(payload.get("workspace"), str(workspace.resolve()))
        self.assertIsInstance(payload.get("pid"), int)
        self.assertEqual(payload.get("orc_pid"), payload.get("pid"))
        self.assertEqual(payload.get("task_id"), "TASK-1")


class DebugLogDirTest(unittest.TestCase):
    def test_debug_log_dir_uses_system_tempdir(self) -> None:
        mocked_tempdir = str(Path("/tmp") / "orc-tests-tempdir")
        try:
            with patch("tempfile.gettempdir", return_value=mocked_tempdir):
                reloaded = importlib.reload(logging_module)
                self.assertEqual(reloaded.DEBUG_LOG_DIR, Path(mocked_tempdir) / "orc")
        finally:
            importlib.reload(logging_module)


class CrashStdoutPayloadTest(unittest.TestCase):
    def test_build_crash_stdout_payload_contains_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = build_crash_stdout_payload(
                entrypoint="orc_core.cli_app:main",
                phase="main",
                exception_type="RuntimeError",
                error="boom",
                traceback_text="Traceback...",
                workspace=tmpdir,
            )

        self.assertEqual(payload.get("event"), "orc_crash_report")
        self.assertEqual(payload.get("entrypoint"), "orc_core.cli_app:main")
        self.assertEqual(payload.get("phase"), "main")
        self.assertEqual(payload.get("exception_type"), "RuntimeError")
        self.assertEqual(payload.get("error"), "boom")
        self.assertEqual(payload.get("traceback"), "Traceback...")
        self.assertEqual(payload.get("workspace"), str(Path(tmpdir).resolve()))
        self.assertIsInstance(payload.get("pid"), int)
        self.assertTrue(str(payload.get("ts", "")).strip())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_emit_crash_stdout_payload_writes_single_json_line(self, stdout_mock: io.StringIO) -> None:
        payload = emit_crash_stdout_payload(
            entrypoint="orc_core.cli_app:main",
            phase="orchestrator.run_async",
            exception_type="OrchestratorUnhandledException",
            error="orchestrator crashed",
            traceback_text="Traceback line",
            workspace=".",
        )
        printed = stdout_mock.getvalue().strip()
        loaded = json.loads(printed)
        self.assertEqual(loaded, payload)
        self.assertEqual(loaded.get("event"), "orc_crash_report")


class CrashHandlersTest(unittest.TestCase):
    def setUp(self) -> None:
        crash_handler_module._cfg.crash_handlers_installed = False

    def test_report_fatal_exception_logs_and_emits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            workspace = str(Path(tmpdir))
            with patch("orc_core.errors.crash_handler.emit_crash_stdout_payload") as emit_mock:
                emit_mock.return_value = {
                    "event": "orc_crash_report",
                    "entrypoint": "orc_core.cli_app:main",
                    "phase": "main",
                    "exception_type": "RuntimeError",
                    "error": "boom",
                    "traceback": "Traceback...",
                    "workspace": workspace,
                    "pid": 123,
                    "ts": "2026-03-01T00:00:00",
                }
                payload = report_fatal_exception(
                    entrypoint="orc_core.cli_app:main",
                    phase="main",
                    exception_type="RuntimeError",
                    error="boom",
                    traceback_text="Traceback...",
                    workspace=workspace,
                    log_path=log_path,
                    source="sys.excepthook",
                )
            self.assertEqual(payload.get("event"), "orc_crash_report")
            lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertTrue(lines)
            record = json.loads(lines[-1])
            self.assertEqual(record.get("message"), "fatal crash captured")
            self.assertEqual(record.get("source"), "sys.excepthook")
            self.assertEqual(record.get("event"), "orc_crash_report")

    def test_install_crash_handlers_sets_sys_and_threading_excepthooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            workspace = str(Path(tmpdir))
            old_sys_hook = crash_handler_module.sys.excepthook
            old_thread_hook = crash_handler_module.threading.excepthook
            with patch("orc_core.errors.crash_handler.faulthandler.enable") as fault_mock, \
                 patch("orc_core.errors.crash_handler.signal.signal"):
                install_crash_handlers(
                    entrypoint="orc_core.cli_app:main",
                    phase="main",
                    workspace=workspace,
                    log_path=log_path,
                )
            try:
                self.assertIsNot(crash_handler_module.sys.excepthook, old_sys_hook)
                self.assertIsNot(crash_handler_module.threading.excepthook, old_thread_hook)
                self.assertTrue(fault_mock.called)
                with patch("orc_core.errors.crash_handler.report_fatal_exception") as report_mock:
                    exc = RuntimeError("boom")
                    tb_obj = exc.__traceback__
                    crash_handler_module.sys.excepthook(type(exc), exc, tb_obj)
                    self.assertTrue(report_mock.called)
            finally:
                crash_handler_module.sys.excepthook = old_sys_hook
                crash_handler_module.threading.excepthook = old_thread_hook

    def test_install_crash_handlers_signal_handler_reports_and_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            workspace = str(Path(tmpdir))
            old_sys_hook = crash_handler_module.sys.excepthook
            old_thread_hook = crash_handler_module.threading.excepthook
            with patch("orc_core.errors.crash_handler.signal.signal") as signal_mock, patch(
                "orc_core.errors.crash_handler.report_fatal_exception"
            ) as report_mock, patch("orc_core.errors.crash_handler.os.killpg"):
                install_crash_handlers(
                    entrypoint="orc_core.cli_app:main",
                    phase="main",
                    workspace=workspace,
                    log_path=log_path,
                )
                self.assertTrue(signal_mock.called)
                registered = None
                for call in signal_mock.call_args_list:
                    if call.args and call.args[0] == crash_handler_module.signal.SIGTERM:
                        registered = call.args[1]
                        break
                self.assertIsNotNone(registered)
                with self.assertRaises(SystemExit) as exit_ctx:
                    registered(crash_handler_module.signal.SIGTERM, None)
                self.assertEqual(exit_ctx.exception.code, 128 + int(crash_handler_module.signal.SIGTERM))
                self.assertTrue(report_mock.called)
            crash_handler_module.sys.excepthook = old_sys_hook
            crash_handler_module.threading.excepthook = old_thread_hook


class TimelineDebugLogTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_debug_enabled = logging_module._cfg.debug_enabled
        self._orig_debug_log_path = logging_module._cfg.debug_log_path

    def tearDown(self) -> None:
        logging_module._cfg.debug_enabled = self._orig_debug_enabled
        logging_module._cfg.debug_log_path = self._orig_debug_log_path

    def test_timeline_event_schema_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "debug.jsonl"
            logging_module._cfg.debug_enabled = False
            logging_module._cfg.debug_log_path = log_path
            init_debug_logging(enabled=True, workdir=tmpdir)
            started_at_ms = timeline_step_started(
                timeline_id="tl-1",
                task_id="TASK-1",
                step="agent_attempt",
                location="tests/test_logging.py:test_timeline_event_schema_is_stable",
                attempt=1,
                data={"k": "v"},
            )
            timeline_instant(
                timeline_id="tl-1",
                task_id="TASK-1",
                step="wait_for_completion_exit",
                location="tests/test_logging.py:test_timeline_event_schema_is_stable",
                attempt=1,
                result="stalled",
                reason="timeout",
            )
            timeline_step_finished(
                timeline_id="tl-1",
                task_id="TASK-1",
                step="agent_attempt",
                location="tests/test_logging.py:test_timeline_event_schema_is_stable",
                attempt=1,
                started_at_ms=started_at_ms,
                result="restart",
                reason="stalled",
            )
            rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            timeline_rows = [row for row in rows if row.get("type") == "debug_timeline"]

        self.assertEqual(len(timeline_rows), 3)
        start_row = timeline_rows[0]
        self.assertEqual(start_row.get("event"), "start")
        self.assertEqual(start_row.get("timeline_id"), "tl-1")
        self.assertEqual(start_row.get("task_id"), "TASK-1")
        self.assertEqual(start_row.get("step"), "agent_attempt")
        self.assertEqual(start_row.get("attempt"), 1)
        self.assertIsInstance(start_row.get("timestamp_ms"), int)

        finish_row = timeline_rows[-1]
        self.assertEqual(finish_row.get("event"), "finish")
        self.assertIsInstance(finish_row.get("duration_ms"), int)
        self.assertGreaterEqual(int(finish_row.get("duration_ms", -1)), 0)
        self.assertEqual(finish_row.get("result"), "restart")
        self.assertEqual(finish_row.get("reason"), "stalled")


class TimelineStepContextManagerTest(unittest.TestCase):
    """Tests for the ``timeline_step`` context manager."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._log_path = Path(self._tmpdir) / "debug.jsonl"
        self._orig_debug_enabled = logging_module._cfg.debug_enabled
        self._orig_debug_log_path = logging_module._cfg.debug_log_path
        logging_module._cfg.debug_enabled = False
        logging_module._cfg.debug_log_path = self._log_path
        init_debug_logging(enabled=True, workdir=self._tmpdir)

    def tearDown(self) -> None:
        logging_module._cfg.debug_enabled = self._orig_debug_enabled
        logging_module._cfg.debug_log_path = self._orig_debug_log_path
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _timeline_rows(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._log_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and json.loads(line).get("type") == "debug_timeline"
        ]

    def test_normal_exit_defaults_to_completed(self) -> None:
        with timeline_step(
            timeline_id="t1", task_id="T-1", step="test_step",
            location="tests/test_logging.py:test_normal_exit",
        ) as ts:
            pass  # no explicit result

        rows = self._timeline_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["event"], "start")
        self.assertEqual(rows[1]["event"], "finish")
        self.assertEqual(rows[1]["result"], "completed")
        self.assertGreaterEqual(rows[1]["duration_ms"], 0)

    def test_exception_defaults_to_failed_and_reraises(self) -> None:
        with self.assertRaises(ValueError):
            with timeline_step(
                timeline_id="t2", task_id="T-2", step="failing_step",
                location="tests/test_logging.py:test_exception",
            ) as ts:
                raise ValueError("boom")

        rows = self._timeline_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["result"], "failed")

    def test_explicit_result_preserved_on_normal_exit(self) -> None:
        with timeline_step(
            timeline_id="t3", task_id="T-3", step="skip_step",
            location="tests/test_logging.py:test_explicit_result",
        ) as ts:
            ts.result = "skipped"
            ts.reason = "already_done"

        rows = self._timeline_rows()
        self.assertEqual(rows[1]["result"], "skipped")
        self.assertEqual(rows[1]["reason"], "already_done")

    def test_explicit_failed_result_on_normal_exit(self) -> None:
        with timeline_step(
            timeline_id="t4", task_id="T-4", step="fail_step",
            location="tests/test_logging.py:test_explicit_failed",
        ) as ts:
            ts.result = "failed"
            ts.reason = "launch_failed"

        rows = self._timeline_rows()
        self.assertEqual(rows[1]["result"], "failed")
        self.assertEqual(rows[1]["reason"], "launch_failed")

    def test_finish_data_passed_through(self) -> None:
        with timeline_step(
            timeline_id="t5", task_id="T-5", step="data_step",
            location="tests/test_logging.py:test_finish_data",
            data={"model": "gpt-4"},
        ) as ts:
            ts.finish_data = {"error": "timeout"}

        rows = self._timeline_rows()
        self.assertEqual(rows[0]["data"], {"model": "gpt-4"})
        self.assertEqual(rows[1]["data"], {"error": "timeout"})

    def test_started_at_ms_accessible(self) -> None:
        with timeline_step(
            timeline_id="t6", task_id="T-6", step="ts_step",
            location="tests/test_logging.py:test_started_at_ms",
        ) as ts:
            self.assertIsInstance(ts.started_at_ms, int)
            self.assertGreater(ts.started_at_ms, 0)


if __name__ == "__main__":
    unittest.main()
