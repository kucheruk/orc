#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from orc_core.project_hooks import fire_hooks


class FireHooksTest(unittest.TestCase):
    def test_does_nothing_when_hooks_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # No .orc/hooks/ directory — should be a no-op
            fire_hooks(tmpdir, "on_move", {"TASK_ID": "T-1"})

    def test_does_nothing_when_no_matching_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / ".orc" / "hooks"
            hooks_dir.mkdir(parents=True)
            (hooks_dir / "on_complete.sh").write_text("#!/bin/sh\necho done")
            (hooks_dir / "on_complete.sh").chmod(0o755)
            # Event is "on_move" but only "on_complete.sh" exists
            with patch("orc_core.project_hooks.subprocess.Popen") as popen_mock:
                fire_hooks(tmpdir, "on_move", {})
                popen_mock.assert_not_called()

    def test_launches_matching_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / ".orc" / "hooks"
            hooks_dir.mkdir(parents=True)
            script = hooks_dir / "on_move.sh"
            script.write_text("#!/bin/sh\necho moved")
            script.chmod(0o755)
            with patch("orc_core.project_hooks.subprocess.Popen") as popen_mock:
                fire_hooks(tmpdir, "on_move", {"CARD_ID": "C-1"})
                popen_mock.assert_called_once()
                call_kwargs = popen_mock.call_args
                env = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env")
                self.assertEqual(env["ORC_EVENT"], "on_move")
                self.assertEqual(env["ORC_WORKSPACE"], tmpdir)
                self.assertEqual(env["CARD_ID"], "C-1")

    def test_ignores_non_executable_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / ".orc" / "hooks"
            hooks_dir.mkdir(parents=True)
            script = hooks_dir / "on_move.sh"
            script.write_text("#!/bin/sh\necho moved")
            # No execute permission
            script.chmod(0o644)
            with patch("orc_core.project_hooks.subprocess.Popen") as popen_mock:
                fire_hooks(tmpdir, "on_move", {})
                popen_mock.assert_not_called()

    def test_swallows_popen_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / ".orc" / "hooks"
            hooks_dir.mkdir(parents=True)
            script = hooks_dir / "on_move.sh"
            script.write_text("#!/bin/sh\necho moved")
            script.chmod(0o755)
            with patch("orc_core.project_hooks.subprocess.Popen", side_effect=OSError("popen failed")):
                # Should not raise
                fire_hooks(tmpdir, "on_move", {})

    def test_swallows_outer_exception(self) -> None:
        # Passing a non-string workdir that would cause Path() to fail
        with patch("orc_core.project_hooks.Path", side_effect=TypeError("bad path")):
            # Should not raise
            fire_hooks(None, "on_move", {})
