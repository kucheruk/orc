#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from textual.app import App
from textual.message_pump import active_app

from orc_core.backlog_status import BacklogStatus
from orc_core.role_config import ROLE_CODER, RoleProfileRegistry
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
            ["mode_set", "task_id", "roles_btn", "start_btn", "cancel_btn"],
        )

    def test_focus_cycle_for_prompt_mode(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(
            screen._focus_cycle_for_mode("prompt"),
            ["mode_set", "prompt_text", "roles_btn", "start_btn", "cancel_btn"],
        )

    def test_focus_cycle_for_backlog_mode(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        self.assertEqual(
            screen._focus_cycle_for_mode("backlog"),
            ["mode_set", "roles_btn", "start_btn", "cancel_btn"],
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

    def test_model_is_synced_from_coder_role_override(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry.update_override(tmpdir, ROLE_CODER, model="sonnet-4.5")
            screen = StartMenuScreen(
                status,
                models=["gpt-5.3-codex", "sonnet-4.5"],
                default_model="gpt-5.3-codex",
                workdir=tmpdir,
                role_registry=registry,
            )
        self.assertEqual(screen._selected_model(), "sonnet-4.5")

    def test_open_role_settings_uses_app_push_screen(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")
        screen._selected_mode = lambda: "backlog"  # type: ignore[method-assign]
        screen._focus_cycle_for_mode = lambda _mode: ["mode_set", "roles_btn", "start_btn"]  # type: ignore[method-assign]
        screen._focused_cycle_id = lambda _cycle: "roles_btn"  # type: ignore[method-assign]
        app = Mock()
        token = active_app.set(app)

        try:
            screen.action_open_role_settings()
        finally:
            active_app.reset(token)

        app.push_screen.assert_called_once()

    def test_open_model_picker_uses_app_push_screen(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")
        screen._selected_mode = lambda: "backlog"  # type: ignore[method-assign]
        screen._focus_cycle_for_mode = lambda _mode: ["mode_set", "roles_btn", "start_btn"]  # type: ignore[method-assign]
        screen._focused_cycle_id = lambda _cycle: "roles_btn"  # type: ignore[method-assign]
        app = Mock()
        token = active_app.set(app)

        try:
            screen.action_open_model_picker()
        finally:
            active_app.reset(token)

        app.push_screen.assert_called_once()

    def test_set_error_escapes_markup_tokens(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        screen = StartMenuScreen(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        class _TestApp(App[None]):
            def compose(self):
                yield screen

        async def _run() -> None:
            async with _TestApp().run_test() as pilot:
                _ = pilot
                screen._set_error("broken [/")
                error = screen.query_one("#error_text")
                self.assertIn("broken [/", str(error.render()))

        import asyncio

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
