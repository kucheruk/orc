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

    def test_resume_mode_is_first_when_resume_available(self) -> None:
        open_tasks = [Task(task_id="TASK-101", text="one", done=False)]
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=open_tasks, open_tasks=open_tasks)
        screen = StartMenuScreen(
            status,
            models=["gpt-5.3-codex"],
            default_model="gpt-5.3-codex",
            resume_task_id="TASK-101",
        )

        self.assertEqual(screen._mode_values[0][0], "resume")
        self.assertIn("TASK-101", screen._mode_values[0][1])

    def test_focus_cycle_for_single_mode(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(
            screen._focus_cycle_for_mode("single"),
            ["mode_set", "task_id", "start_btn", "cancel_btn"],
        )

    def test_focus_cycle_for_prompt_mode(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(
            screen._focus_cycle_for_mode("prompt"),
            ["mode_set", "prompt_text", "start_btn", "cancel_btn"],
        )

    def test_focus_cycle_for_backlog_mode(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(
            screen._focus_cycle_for_mode("backlog"),
            ["mode_set", "start_btn", "cancel_btn"],
        )

    def test_selected_model_defaults_to_default_model(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex", "o3"], default_model="o3")
        self.assertEqual(screen._selected_model(), "o3")

    def test_mode_field_visibility_rules(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertTrue(screen._is_task_input_visible("single"))
        self.assertFalse(screen._is_task_input_visible("prompt"))
        self.assertFalse(screen._is_task_input_visible("backlog"))

        self.assertTrue(screen._is_prompt_input_visible("prompt"))
        self.assertFalse(screen._is_prompt_input_visible("single"))
        self.assertFalse(screen._is_prompt_input_visible("backlog"))


if __name__ == "__main__":
    unittest.main()
