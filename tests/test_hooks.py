#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.atomic_io import write_json_atomic
from orc_core.hooks import ensure_repo_hooks, write_task_file
from orc_core.hooks import update_task_restart_count
from orc_core.task_source import MarkdownTaskSource, Task


def _git(args: list[str], cwd: Path) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")


class HooksStopBehaviorTest(unittest.TestCase):
    def test_stop_backfills_conversation_id_from_payload_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            backlog = tmpdir / "BACKLOG.md"
            log_path = tmpdir / ".orc" / "orc.log"
            backlog.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")

            _, stop_path = ensure_repo_hooks(str(tmpdir))
            write_task_file(
                str(tmpdir),
                Task(task_id="TASK-001", text="test task", done=False),
                backlog,
                log_path,
            )
            task_path = tmpdir / ".cursor" / "orc-task.json"

            payload = {"status": "error", "loop_count": 0, "conversation_id": "conv-123"}
            env = os.environ.copy()
            env["ORC_TELEGRAM_DISABLE"] = "1"
            result = subprocess.run(
                ["python3", str(stop_path)],
                cwd=tmpdir,
                env=env,
                input=json.dumps(payload),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            task_payload = json.loads(task_path.read_text(encoding="utf-8"))
            self.assertEqual(task_payload.get("conversation_id"), "conv-123")

    def test_stop_does_not_mark_task_done_on_clean_tree_without_recent_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            backlog = tmpdir / "BACKLOG.md"
            log_path = tmpdir / ".orc" / "orc.log"
            backlog.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")
            (tmpdir / ".gitignore").write_text(".cursor/\n.orc/\n", encoding="utf-8")

            _git(["init"], tmpdir)
            _git(["add", "BACKLOG.md", ".gitignore"], tmpdir)
            _git(
                ["-c", "user.name=orc-test", "-c", "user.email=orc-test@example.com", "commit", "-m", "init"],
                tmpdir,
            )

            _, stop_path = ensure_repo_hooks(str(tmpdir))
            write_task_file(
                str(tmpdir),
                Task(task_id="TASK-001", text="test task", done=False),
                backlog,
                log_path,
            )
            task_path = tmpdir / ".cursor" / "orc-task.json"
            task_payload = json.loads(task_path.read_text(encoding="utf-8"))
            task_payload["created_at"] = "2999-01-01T00:00:00Z"
            task_path.write_text(json.dumps(task_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            payload = {"status": "completed", "loop_count": 0, "conversation_id": ""}
            env = os.environ.copy()
            env["ORC_TELEGRAM_DISABLE"] = "1"
            result = subprocess.run(
                ["python3", str(stop_path)],
                cwd=tmpdir,
                env=env,
                input=json.dumps(payload),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertFalse(MarkdownTaskSource(backlog).is_task_done("TASK-001"))
            self.assertTrue(task_path.exists())


class HooksAtomicWriteTest(unittest.TestCase):
    def test_write_task_file_does_not_use_path_write_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            backlog = tmpdir / "BACKLOG.md"
            backlog.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")
            log_path = tmpdir / ".orc" / "orc.log"
            task = Task(task_id="TASK-001", text="test task", done=False)

            with patch.object(Path, "write_text", side_effect=RuntimeError("Path.write_text should not be used")):
                task_path = write_task_file(str(tmpdir), task, backlog, log_path)

            self.assertTrue(task_path.exists())
            self.assertIn('"task_id": "TASK-001"', task_path.read_text(encoding="utf-8"))

    def test_update_task_restart_count_does_not_use_path_write_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            task_path = tmpdir / ".cursor" / "orc-task.json"
            log_path = tmpdir / ".orc" / "orc.log"
            write_json_atomic(
                task_path,
                {
                    "version": 1,
                    "task_id": "TASK-001",
                    "task_text": "test task",
                    "backlog_path": str(tmpdir / "BACKLOG.md"),
                    "workspace_root": str(tmpdir),
                    "conversation_id": "",
                    "created_at": "2026-01-01T00:00:00",
                    "restart_count": 0,
                },
            )

            with patch.object(Path, "write_text", side_effect=RuntimeError("Path.write_text should not be used")):
                update_task_restart_count(task_path, log_path, restart_count=2)

            self.assertIn('"restart_count": 2', task_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
