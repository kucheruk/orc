#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.task_source import MarkdownTaskSource


class TaskSourceTest(unittest.TestCase):
    def _write_backlog(self, content: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tmpdir = tempfile.TemporaryDirectory()
        path = Path(tmpdir.name) / "BACKLOG.md"
        path.write_text(content, encoding="utf-8")
        return tmpdir, path

    def test_list_tasks_separates_done_and_open(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [ ] TASK-001 first\n"
            "- [x] TASK-002 second\n"
            "- [ ] TASK-003 third\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        tasks = source.list_tasks()

        self.assertEqual([task.task_id for task in tasks], ["TASK-001", "TASK-002", "TASK-003"])
        self.assertEqual([task.done for task in tasks], [False, True, False])
        self.assertEqual([task.task_id for task in tasks if not task.done], ["TASK-001", "TASK-003"])

    def test_get_first_open_task_returns_first_unfinished(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [x] TASK-001 done\n"
            "- [ ] TASK-002 open\n"
            "- [ ] TASK-003 open\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        first_open = source.get_first_open_task()

        self.assertIsNotNone(first_open)
        assert first_open is not None
        self.assertEqual(first_open.task_id, "TASK-002")
        self.assertFalse(first_open.done)

    def test_mark_task_done_updates_backlog_and_status(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [ ] TASK-010 do work\n"
            "- [ ] TASK-011 do next\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        marked = source.mark_task_done("TASK-010")

        self.assertTrue(marked)
        self.assertTrue(source.is_task_done("TASK-010"))
        self.assertIn("- [x] TASK-010 do work", path.read_text(encoding="utf-8"))

    def test_mark_task_done_returns_false_when_task_missing(self) -> None:
        tmpdir, path = self._write_backlog("- [ ] TASK-100 existing\n")
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        marked = source.mark_task_done("TASK-999")

        self.assertFalse(marked)
        self.assertIn("- [ ] TASK-100 existing", path.read_text(encoding="utf-8"))

    def test_get_open_tasks_returns_only_unfinished(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [x] TASK-001 done\n"
            "- [ ] TASK-002 open\n"
            "- [ ] TASK-003 open\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        open_tasks = source.get_open_tasks()

        self.assertEqual([task.task_id for task in open_tasks], ["TASK-002", "TASK-003"])

    def test_get_task_by_id_returns_task_or_none(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [x] TASK-001 done\n"
            "- [ ] TASK-002 open\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        selected = source.get_task_by_id("TASK-002")
        missing = source.get_task_by_id("TASK-999")

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.task_id, "TASK-002")
        self.assertFalse(selected.done)
        self.assertIsNone(missing)


if __name__ == "__main__":
    unittest.main()
