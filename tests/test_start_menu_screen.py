#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path

from orc_core.backlog_status import BacklogStatus
from orc_core.task_source import Task
from orc_core.tui.screens.start_menu import StartMenuScreen


class StartMenuScreenTaskHintsTest(unittest.TestCase):
    def test_available_task_ids_hint_includes_open_task_ids(self) -> None:
        open_tasks = [
            Task(task_id="TASK-101", text="one", done=False),
            Task(task_id="TASK-102", text="two", done=False),
        ]
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=open_tasks, open_tasks=open_tasks)
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        hint = screen._available_task_ids_hint()

        self.assertIn("TASK-101", hint)
        self.assertIn("TASK-102", hint)

    def test_available_task_ids_hint_when_no_open_tasks(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        hint = screen._available_task_ids_hint()

        self.assertIn("Нет открытых задач", hint)


if __name__ == "__main__":
    unittest.main()
