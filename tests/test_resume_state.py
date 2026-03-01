#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path

from orc_core.resume_state import resumable_task_id


class ResumeStateConversationIdTest(unittest.TestCase):
    def test_resumable_task_id_returns_empty_when_conversation_id_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backlog = root / "BACKLOG.md"
            backlog.write_text("- [ ] TASK-001 continue\n", encoding="utf-8")
            task_path = root / ".cursor" / "orc-task.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001",
                        "backlog_path": str(backlog),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self.assertEqual(resumable_task_id(task_path, backlog), "")

    def test_resumable_task_id_returns_empty_when_conversation_id_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backlog = root / "BACKLOG.md"
            backlog.write_text("- [ ] TASK-001 continue\n", encoding="utf-8")
            task_path = root / ".cursor" / "orc-task.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001",
                        "conversation_id": "   ",
                        "backlog_path": str(backlog),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self.assertEqual(resumable_task_id(task_path, backlog), "")


if __name__ == "__main__":
    unittest.main()
