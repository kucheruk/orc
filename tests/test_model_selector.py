#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.model_selector import (
    DEFAULT_MODEL,
    ModelSelectionError,
    choose_model_interactive,
    list_supported_models,
    load_last_selected_model,
    save_last_selected_model,
)


class ModelSelectorStateTest(unittest.TestCase):
    def test_load_last_selected_model_returns_none_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsNone(load_last_selected_model(tmpdir))

    def test_save_then_load_last_selected_model_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            save_last_selected_model(tmpdir, "gpt-5.3-codex")
            self.assertEqual(load_last_selected_model(tmpdir), "gpt-5.3-codex")

    def test_load_last_selected_model_raises_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".orc" / "model-selection.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ModelSelectionError):
                load_last_selected_model(tmpdir)

    def test_default_model_constant(self) -> None:
        self.assertEqual(DEFAULT_MODEL, "gpt-5.3-codex")


class ModelSelectorCommandTest(unittest.TestCase):
    @patch("orc_core.model_selector.subprocess.run")
    def test_list_supported_models_parses_non_empty_lines(self, run_mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = "gpt-5.3-codex\nsonnet-4.5\n\n"
        run_mock.return_value.stderr = ""
        models = list_supported_models()
        self.assertEqual(models, ["gpt-5.3-codex", "sonnet-4.5"])

    @patch("orc_core.model_selector.subprocess.run")
    def test_list_supported_models_raises_when_empty(self, run_mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = "\n\n"
        run_mock.return_value.stderr = ""
        with self.assertRaises(ModelSelectionError):
            list_supported_models()


class ModelSelectorUiTest(unittest.TestCase):
    @patch("orc_core.model_selector.radiolist_dialog")
    def test_choose_model_interactive_prefers_requested_default(self, dialog_mock) -> None:
        dialog_mock.return_value.run.return_value = "sonnet-4.5"
        selected = choose_model_interactive(["gpt-5.3-codex", "sonnet-4.5"], "sonnet-4.5")
        self.assertEqual(selected, "sonnet-4.5")

    @patch("orc_core.model_selector.radiolist_dialog")
    def test_choose_model_interactive_raises_on_cancel(self, dialog_mock) -> None:
        dialog_mock.return_value.run.return_value = None
        with self.assertRaises(KeyboardInterrupt):
            choose_model_interactive(["gpt-5.3-codex"], "gpt-5.3-codex")

    @patch("orc_core.model_selector.radiolist_dialog")
    def test_choose_model_interactive_raises_on_empty_models(self, _dialog_mock) -> None:
        with self.assertRaises(ModelSelectionError):
            choose_model_interactive([], "gpt-5.3-codex")


if __name__ == "__main__":
    unittest.main()
