#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import io
import importlib
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

import orc_core.logging as logging_module
from orc_core.logging import (
    build_crash_stdout_payload,
    emit_crash_stdout_payload,
    install_crash_handlers,
    log_event,
    report_fatal_exception,
    set_log_context,
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
        logging_module._CRASH_HANDLERS_INSTALLED = False

    def test_report_fatal_exception_logs_and_emits_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            workspace = str(Path(tmpdir))
            with patch("orc_core.logging.emit_crash_stdout_payload") as emit_mock:
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
            old_sys_hook = logging_module.sys.excepthook
            old_thread_hook = logging_module.threading.excepthook
            install_crash_handlers(
                entrypoint="orc_core.cli_app:main",
                phase="main",
                workspace=workspace,
                log_path=log_path,
            )
            try:
                self.assertIsNot(logging_module.sys.excepthook, old_sys_hook)
                self.assertIsNot(logging_module.threading.excepthook, old_thread_hook)
                with patch("orc_core.logging.report_fatal_exception") as report_mock:
                    exc = RuntimeError("boom")
                    tb = traceback.TracebackException.from_exception(exc)
                    tb_obj = exc.__traceback__
                    logging_module.sys.excepthook(type(exc), exc, tb_obj)
                    self.assertTrue(report_mock.called)
            finally:
                logging_module.sys.excepthook = old_sys_hook
                logging_module.threading.excepthook = old_thread_hook

    def test_install_crash_handlers_signal_handler_reports_and_exits(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "orc.log"
            workspace = str(Path(tmpdir))
            old_sys_hook = logging_module.sys.excepthook
            old_thread_hook = logging_module.threading.excepthook
            with patch("orc_core.logging.signal.signal") as signal_mock, patch(
                "orc_core.logging.report_fatal_exception"
            ) as report_mock:
                install_crash_handlers(
                    entrypoint="orc_core.cli_app:main",
                    phase="main",
                    workspace=workspace,
                    log_path=log_path,
                )
                self.assertTrue(signal_mock.called)
                registered = None
                for call in signal_mock.call_args_list:
                    if call.args and call.args[0] == logging_module.signal.SIGTERM:
                        registered = call.args[1]
                        break
                self.assertIsNotNone(registered)
                with self.assertRaises(SystemExit) as exit_ctx:
                    registered(logging_module.signal.SIGTERM, None)
                self.assertEqual(exit_ctx.exception.code, 128 + int(logging_module.signal.SIGTERM))
                self.assertTrue(report_mock.called)
            logging_module.sys.excepthook = old_sys_hook
            logging_module.threading.excepthook = old_thread_hook


if __name__ == "__main__":
    unittest.main()
