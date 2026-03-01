#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.backlog_status import BacklogStatus
from orc_core.start_menu import StartMenuChoice, show_start_menu
from orc_core.task_source import Task


class StartMenuBridgeTest(unittest.TestCase):
    @patch("orc_core.tui_app.run_start_menu")
    def test_show_start_menu_returns_choice_from_textual(self, run_start_menu) -> None:
        run_start_menu.return_value = StartMenuChoice(mode="backlog", debug_enabled=True, model="gpt-5.3-codex")
        task = Task(task_id="TASK-001", text="test", done=False)
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[task], open_tasks=[task])

        choice = show_start_menu(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(choice, StartMenuChoice(mode="backlog", debug_enabled=True, model="gpt-5.3-codex"))

    @patch("orc_core.tui_app.run_start_menu", return_value=None)
    def test_show_start_menu_raises_keyboard_interrupt_on_cancel(self, _run_start_menu) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])

        with self.assertRaises(KeyboardInterrupt):
            show_start_menu(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

if __name__ == "__main__":
    unittest.main()
