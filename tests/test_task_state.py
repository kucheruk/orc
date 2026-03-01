#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.atomic_io import write_json_atomic
from orc_core.task_state import get_resume_id_from_agent_ls, update_task_conversation_id


class TaskStateAtomicWriteTest(unittest.TestCase):
    def test_update_task_conversation_id_does_not_use_path_write_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_path = root / ".cursor" / "orc-task.json"
            log_path = root / ".orc" / "orc.log"
            write_json_atomic(
                task_path,
                {
                    "version": 1,
                    "task_id": "TASK-001",
                    "task_text": "test task",
                    "backlog_path": str(root / "BACKLOG.md"),
                    "workspace_root": str(root),
                    "conversation_id": "",
                    "created_at": "2026-01-01T00:00:00",
                    "restart_count": 0,
                },
            )

            with patch.object(Path, "write_text", side_effect=RuntimeError("Path.write_text should not be used")):
                update_task_conversation_id(task_path, log_path, "conv-123")

            payload = task_path.read_text(encoding="utf-8")
            self.assertIn('"conversation_id": "conv-123"', payload)

    @patch("orc_core.task_state.subprocess.run")
    def test_get_resume_id_from_agent_ls_timeout_returns_none(self, run_mock) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="agent ls", timeout=15.0)
        with tempfile.TemporaryDirectory() as tmpdir:
            resume_id = get_resume_id_from_agent_ls(tmpdir, Path(tmpdir) / ".orc" / "orc.log")
        self.assertIsNone(resume_id)


if __name__ == "__main__":
    unittest.main()
