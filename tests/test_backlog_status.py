#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.backlog_status import inspect_backlog


class BacklogStatusTest(unittest.TestCase):
    def _write_backlog(self, content: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tmpdir = tempfile.TemporaryDirectory()
        path = Path(tmpdir.name) / "BACKLOG.md"
        path.write_text(content, encoding="utf-8")
        return tmpdir, path

    def test_inspect_backlog_reports_hidden_open_tasks_in_markdown_fence(self) -> None:
        tmpdir, path = self._write_backlog(
            "# Backlog\n\n"
            "```markdown\n"
            "- [ ] SEC-006 Hidden task → tasks/SEC-006.md\n"
            "- [x] SEC-005 Done task → tasks/SEC-005.md\n"
            "```\n"
        )
        self.addCleanup(tmpdir.cleanup)

        status = inspect_backlog(path)

        self.assertEqual(status.open_tasks, [])
        self.assertIn("SEC-006", status.disabled_reason)
        self.assertIn("```markdown```", status.disabled_reason)

    def test_inspect_backlog_does_not_treat_plain_code_fence_example_as_hidden_task(self) -> None:
        tmpdir, path = self._write_backlog(
            "## Формат задачи\n\n"
            "```\n"
            "- [ ] AREA-NNN Заголовок\n"
            "```\n"
        )
        self.addCleanup(tmpdir.cleanup)

        status = inspect_backlog(path)

        self.assertEqual(status.disabled_reason, "В backlog нет валидных задач с ID")


if __name__ == "__main__":
    unittest.main()
