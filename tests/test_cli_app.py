#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from orc_core.cli_app import _resolve_mode, _resolve_model
from orc_core.model_selector import DEFAULT_MODEL
from orc_core.start_menu import StartMenuChoice


def _args() -> Namespace:
    return Namespace(
        mode="",
        task_id="",
        prompt="",
        task="",
        model="",
        debug=False,
    )


class CliAppModeSelectionTest(unittest.TestCase):
    @patch("orc_core.cli_app.show_start_menu")
    def test_legacy_task_promotes_to_prompt_mode(self, show_start_menu) -> None:
        args = _args()
        args.task = "do thing"

        _resolve_mode(args, Path("BACKLOG.md"))

        self.assertEqual(args.mode, "prompt")
        self.assertEqual(args.prompt, "do thing")
        show_start_menu.assert_not_called()

    @patch("orc_core.cli_app.show_start_menu")
    def test_explicit_task_id_uses_single_mode_without_menu(self, show_start_menu) -> None:
        args = _args()
        args.task_id = "TASK-001"

        _resolve_mode(args, Path("BACKLOG.md"))

        self.assertEqual(args.mode, "single")
        show_start_menu.assert_not_called()

    @patch("orc_core.cli_app.show_start_menu")
    def test_menu_choice_populates_mode_values(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="single", task_id="TASK-002")

        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(args, Path(tmpdir) / "BACKLOG.md")

        self.assertEqual(args.mode, "single")
        self.assertEqual(args.task_id, "TASK-002")


class _FakeLoader:
    def __init__(self, models: list[str]) -> None:
        self.models = models

    def result(self, timeout: float | None = None) -> list[str]:
        return self.models


class CliAppModelSelectionTest(unittest.TestCase):
    @patch("orc_core.cli_app.save_last_selected_model")
    @patch("orc_core.cli_app.choose_model_interactive")
    @patch("orc_core.cli_app.load_last_selected_model")
    def test_interactive_selection_uses_saved_model_default(
        self,
        load_last_selected_model,
        choose_model_interactive,
        save_last_selected_model,
    ) -> None:
        args = _args()
        load_last_selected_model.return_value = "sonnet-4.5"
        choose_model_interactive.return_value = "sonnet-4.5"
        loader = _FakeLoader(models=["gpt-5.3-codex", "sonnet-4.5"])

        _resolve_model(args, "/tmp/workspace", interactive_requested=True, model_loader=loader)

        self.assertEqual(args.model, "sonnet-4.5")
        choose_model_interactive.assert_called_once_with(
            ["gpt-5.3-codex", "sonnet-4.5"],
            default_model="sonnet-4.5",
        )
        save_last_selected_model.assert_called_once_with("/tmp/workspace", "sonnet-4.5")

    @patch("orc_core.cli_app.save_last_selected_model")
    @patch("orc_core.cli_app.choose_model_interactive")
    def test_non_interactive_without_explicit_model_uses_default(
        self,
        choose_model_interactive,
        save_last_selected_model,
    ) -> None:
        args = _args()

        _resolve_model(args, "/tmp/workspace", interactive_requested=False, model_loader=None)

        self.assertEqual(args.model, DEFAULT_MODEL)
        choose_model_interactive.assert_not_called()
        save_last_selected_model.assert_not_called()

    @patch("orc_core.cli_app.save_last_selected_model")
    @patch("orc_core.cli_app.choose_model_interactive")
    def test_explicit_model_bypasses_selector(self, choose_model_interactive, save_last_selected_model) -> None:
        args = _args()
        args.model = "o3"
        loader = _FakeLoader(models=["gpt-5.3-codex"])

        _resolve_model(args, "/tmp/workspace", interactive_requested=True, model_loader=loader)

        self.assertEqual(args.model, "o3")
        choose_model_interactive.assert_not_called()
        save_last_selected_model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
