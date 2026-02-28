#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from orc_core.cli_app import _resolve_mode, _resolve_model
from orc_core.model_selector import DEFAULT_MODEL
from orc_core.model_selector import ModelSelectionError
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
        show_start_menu.return_value = StartMenuChoice(mode="single", task_id="TASK-002", model="gpt-5.3-codex")

        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
            )

        self.assertEqual(args.mode, "single")
        self.assertEqual(args.task_id, "TASK-002")
        self.assertEqual(args.model, "gpt-5.3-codex")


class CliAppModelSelectionTest(unittest.TestCase):
    @patch("orc_core.cli_app.save_last_selected_model")
    def test_interactive_selection_persists_selected_model(self, save_last_selected_model) -> None:
        args = _args()
        args.model = "sonnet-4.5"

        _resolve_model(args, "/tmp/workspace", interactive_requested=True, model_loader=None)

        self.assertEqual(args.model, "sonnet-4.5")
        save_last_selected_model.assert_called_once_with("/tmp/workspace", "sonnet-4.5")

    @patch("orc_core.cli_app.save_last_selected_model")
    def test_non_interactive_without_explicit_model_uses_default(
        self,
        save_last_selected_model,
    ) -> None:
        args = _args()

        _resolve_model(args, "/tmp/workspace", interactive_requested=False, model_loader=None)

        self.assertEqual(args.model, DEFAULT_MODEL)
        save_last_selected_model.assert_not_called()

    def test_interactive_requires_preselected_model(self) -> None:
        args = _args()
        with self.assertRaises(ModelSelectionError):
            _resolve_model(args, "/tmp/workspace", interactive_requested=True, model_loader=None)


if __name__ == "__main__":
    unittest.main()
