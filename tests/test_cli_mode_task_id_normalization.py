#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from orc_core.cli_app import _resolve_mode
from orc_core.start_menu import StartMenuChoice


def _args() -> Namespace:
    return Namespace(mode="", task_id="", prompt="", task="", model="", debug=False)


class CliModeTaskIdNormalizationTest(unittest.TestCase):
    @patch("orc_core.cli_app.show_start_menu")
    def test_backlog_choice_clears_task_id_from_menu_payload(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="backlog", task_id="TASK-999", model="gpt-5.3-codex")
        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
            )
        self.assertEqual(args.mode, "backlog")
        self.assertEqual(args.task_id, "")

    @patch("orc_core.cli_app.show_start_menu")
    def test_resume_choice_maps_to_backlog_and_clears_task_id(self, show_start_menu) -> None:
        args = _args()
        show_start_menu.return_value = StartMenuChoice(mode="resume", task_id="TASK-123", model="gpt-5.3-codex")
        with tempfile.TemporaryDirectory() as tmpdir:
            _resolve_mode(
                args,
                Path(tmpdir) / "BACKLOG.md",
                models=["gpt-5.3-codex"],
                default_model="gpt-5.3-codex",
            )
        self.assertEqual(args.mode, "backlog")
        self.assertEqual(args.task_id, "")


if __name__ == "__main__":
    unittest.main()
