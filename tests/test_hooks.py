#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from orc_core.hooks import ensure_repo_hooks, write_task_file
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
    def test_stop_marks_task_done_without_forced_retry_on_clean_tree(self) -> None:
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

            payload = {"status": "completed", "loop_count": 0, "conversation_id": ""}
            result = subprocess.run(
                ["python3", str(stop_path)],
                cwd=tmpdir,
                input=json.dumps(payload),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(MarkdownTaskSource(backlog).is_task_done("TASK-001"))
            self.assertFalse((tmpdir / ".cursor" / "orc-task.json").exists())


if __name__ == "__main__":
    unittest.main()
