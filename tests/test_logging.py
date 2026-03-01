#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.logging import log_event, set_log_context


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


if __name__ == "__main__":
    unittest.main()
