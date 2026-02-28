#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.backlog_status import BacklogStatus
from orc_core.start_menu import StartMenuChoice, show_start_menu
from orc_core.task_source import Task


class StartMenuSingleScreenTest(unittest.TestCase):
    @patch("orc_core.start_menu._pick_start_options")
    def test_show_start_menu_returns_mode_debug_and_model(self, pick_start_options) -> None:
        pick_start_options.return_value = ("backlog", "gpt-5.3-codex", True)
        task = Task(task_id="TASK-001", text="test", done=False)
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[task], open_tasks=[task])

        choice = show_start_menu(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(choice, StartMenuChoice(mode="backlog", debug_enabled=True, model="gpt-5.3-codex"))

    @patch("orc_core.start_menu._read_prompt_textarea")
    @patch("orc_core.start_menu.message_dialog")
    @patch("orc_core.start_menu._pick_start_options")
    def test_show_start_menu_retries_when_backlog_mode_unavailable(
        self,
        pick_start_options,
        message_dialog,
        read_prompt_textarea,
    ) -> None:
        pick_start_options.side_effect = [
            ("single", "gpt-5.3-codex", False),
            ("prompt", "gpt-5.3-codex", False),
        ]
        message_dialog.return_value.run.return_value = None
        read_prompt_textarea.return_value = "manual task"
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])

        choice = show_start_menu(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(choice.mode, "prompt")
        self.assertEqual(choice.model, "gpt-5.3-codex")
        self.assertEqual(choice.prompt_text, "manual task")
        self.assertEqual(pick_start_options.call_count, 2)

if __name__ == "__main__":
    unittest.main()
