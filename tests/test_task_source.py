#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.tasks.backlog.source import MarkdownTaskSource


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

    def test_duplicate_task_ids_do_not_leave_open_copy(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [x] REFACT-012 done copy\n"
            "- [ ] REFACT-012 open copy\n"
            "- [ ] TASK-999 next\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        selected = source.get_task_by_id("REFACT-012")
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertFalse(selected.done)
        self.assertFalse(source.is_task_done("REFACT-012"))

        marked = source.mark_task_done("REFACT-012")
        self.assertTrue(marked)
        self.assertTrue(source.is_task_done("REFACT-012"))

        backlog_text = path.read_text(encoding="utf-8")
        self.assertIn("- [x] REFACT-012 done copy", backlog_text)
        self.assertIn("- [x] REFACT-012 open copy", backlog_text)

    def test_list_tasks_supports_link_wrapped_id(self) -> None:
        tmpdir, path = self._write_backlog("- [ ] [TASK-201](https://example.com) linked title\n")
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        tasks = source.list_tasks()

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].task_id, "TASK-201")
        self.assertEqual(tasks[0].text, "TASK-201 linked title")
        self.assertFalse(tasks[0].done)

    def test_list_tasks_supports_nested_checklists(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [ ] TASK-300 parent\n"
            "  - [x] TASK-301 child done\n"
            "  - [ ] TASK-302 child open\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        tasks = source.list_tasks()

        self.assertEqual([task.task_id for task in tasks], ["TASK-300", "TASK-301", "TASK-302"])
        self.assertEqual([task.done for task in tasks], [False, True, False])

    def test_list_tasks_ignores_checkbox_like_lines_in_code_fence(self) -> None:
        tmpdir, path = self._write_backlog(
            "```md\n"
            "- [ ] TASK-900 not real\n"
            "```\n"
            "- [ ] TASK-901 real\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        tasks = source.list_tasks()

        self.assertEqual([task.task_id for task in tasks], ["TASK-901"])

    def test_mark_task_done_preserves_markdown_formatting(self) -> None:
        tmpdir, path = self._write_backlog("- [ ] [TASK-777](https://example.com) сохранить формат\n")
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        marked = source.mark_task_done("TASK-777")

        self.assertTrue(marked)
        self.assertIn("- [x] [TASK-777](https://example.com) сохранить формат", path.read_text(encoding="utf-8"))

    def test_report_link_does_not_change_checkbox_status(self) -> None:
        tmpdir, path = self._write_backlog(
            "- [ ] INFRA-001 Solution Structure → tasks/INFRA-001.md\n"
            "- [ ] INFRA-002 Next task\n"
        )
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        tasks = source.list_tasks()

        self.assertEqual([task.task_id for task in tasks], ["INFRA-001", "INFRA-002"])
        self.assertEqual([task.done for task in tasks], [False, False])
        self.assertFalse(source.is_task_done("INFRA-001"))
        first_open = source.get_first_open_task()
        self.assertIsNotNone(first_open)
        assert first_open is not None
        self.assertEqual(first_open.task_id, "INFRA-001")

    def test_report_link_with_other_task_id_does_not_mark_done(self) -> None:
        tmpdir, path = self._write_backlog("- [ ] INFRA-001 Solution Structure → tasks/INFRA-002.md\n")
        self.addCleanup(tmpdir.cleanup)
        source = MarkdownTaskSource(path)

        tasks = source.list_tasks()

        self.assertEqual(len(tasks), 1)
        self.assertFalse(tasks[0].done)
        self.assertFalse(source.is_task_done("INFRA-001"))


if __name__ == "__main__":
    unittest.main()
