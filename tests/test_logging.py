#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import io
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import orc_core.logging as logging_module
from orc_core.logging import build_crash_stdout_payload, emit_crash_stdout_payload, log_event, set_log_context


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


if __name__ == "__main__":
    unittest.main()
