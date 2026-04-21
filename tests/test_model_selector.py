#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.cli.model_selector import (
    DEFAULT_MODEL,
    ModelSelectionError,
    choose_model_interactive,
    list_supported_models,
    load_last_selected_model,
    save_last_selected_model,
)
from orc_core.infra.io.state_paths import model_selection_path


class _IsolatedStateRoot:
    """Context manager: redirect ORC_STATE_ROOT to a fresh tmpdir so tests
    don't leak files into the user's real state directory."""

    def __enter__(self) -> str:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("ORC_STATE_ROOT")
        os.environ["ORC_STATE_ROOT"] = self._tmp.name
        return self._tmp.name

    def __exit__(self, *_exc) -> None:
        if self._prev is None:
            os.environ.pop("ORC_STATE_ROOT", None)
        else:
            os.environ["ORC_STATE_ROOT"] = self._prev
        self._tmp.cleanup()


class ModelSelectorStateTest(unittest.TestCase):
    def test_load_last_selected_model_returns_none_when_file_missing(self) -> None:
        with _IsolatedStateRoot(), tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsNone(load_last_selected_model(tmpdir))

    def test_save_then_load_last_selected_model_roundtrip(self) -> None:
        with _IsolatedStateRoot(), tempfile.TemporaryDirectory() as tmpdir:
            save_last_selected_model(tmpdir, "gpt-5.3-codex")
            self.assertEqual(load_last_selected_model(tmpdir), "gpt-5.3-codex")

    def test_load_last_selected_model_raises_for_invalid_json(self) -> None:
        with _IsolatedStateRoot(), tempfile.TemporaryDirectory() as tmpdir:
            path = model_selection_path(tmpdir)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ModelSelectionError):
                load_last_selected_model(tmpdir)

    def test_default_model_constant(self) -> None:
        self.assertEqual(DEFAULT_MODEL, "gpt-5.3-codex")

    def test_save_last_selected_model_does_not_use_path_write_text(self) -> None:
        with _IsolatedStateRoot(), tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "write_text", side_effect=RuntimeError("Path.write_text should not be used")):
                save_last_selected_model(tmpdir, "gpt-5.3-codex")
            self.assertEqual(load_last_selected_model(tmpdir), "gpt-5.3-codex")


class ModelSelectorCommandTest(unittest.TestCase):
    @patch("orc_core.cli.model_selector.subprocess.run")
    def test_list_supported_models_parses_non_empty_lines(self, run_mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = "gpt-5.3-codex - GPT 5.3 Codex\nsonnet-4.5 - Sonnet\n\n"
        run_mock.return_value.stderr = ""
        models = list_supported_models()
        self.assertEqual(models, ["gpt-5.3-codex", "sonnet-4.5"])

    @patch("orc_core.cli.model_selector.subprocess.run")
    def test_list_supported_models_ignores_ansi_and_non_model_lines(self, run_mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = (
            "\x1b[2K\x1b[GLoading models...\n"
            "\x1b[2K\x1b[GAvailable models\n"
            "auto - Auto\n"
            "gpt-5.3-codex - GPT 5.3 Codex\n"
            "composer-1.5 - Composer\n"
        )
        run_mock.return_value.stderr = ""
        models = list_supported_models()
        self.assertEqual(models, ["auto", "gpt-5.3-codex", "composer-1.5"])

    @patch("orc_core.cli.model_selector.subprocess.run")
    def test_list_supported_models_raises_when_empty(self, run_mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = "\n\n"
        run_mock.return_value.stderr = ""
        with self.assertRaises(ModelSelectionError):
            list_supported_models()

    @patch("orc_core.cli.model_selector.subprocess.run")
    def test_list_supported_models_raises_on_timeout(self, run_mock) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="agent --list-models", timeout=15.0)
        with self.assertRaises(ModelSelectionError):
            list_supported_models()


class ModelSelectorUiTest(unittest.TestCase):
    def test_choose_model_interactive_prefers_requested_default(self) -> None:
        selected = choose_model_interactive(["gpt-5.3-codex", "sonnet-4.5"], "sonnet-4.5")
        self.assertEqual(selected, "sonnet-4.5")

    def test_choose_model_interactive_falls_back_to_first_when_default_missing(self) -> None:
        selected = choose_model_interactive(["gpt-5.3-codex", "sonnet-4.5"], "missing-model")
        self.assertEqual(selected, "gpt-5.3-codex")

    def test_choose_model_interactive_raises_on_empty_models(self) -> None:
        with self.assertRaises(ModelSelectionError):
            choose_model_interactive([], "gpt-5.3-codex")


if __name__ == "__main__":
    unittest.main()
