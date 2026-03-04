#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.gitignore_guard import REQUIRED_ORC_IGNORE_SNIPPET, validate_workspace_gitignore


class GitignoreGuardTest(unittest.TestCase):
    def test_valid_when_orc_rule_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".gitignore"
            path.write_text("bin/\n.orc/\n", encoding="utf-8")
            ok, error = validate_workspace_gitignore(tmpdir)
        self.assertTrue(ok)
        self.assertEqual(error, "")

    def test_invalid_when_gitignore_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ok, error = validate_workspace_gitignore(tmpdir)
        self.assertFalse(ok)
        self.assertIn(".gitignore", error)
        self.assertIn("copy-paste", error)
        self.assertIn(REQUIRED_ORC_IGNORE_SNIPPET.strip(), error)

    def test_invalid_when_orc_rule_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".gitignore"
            path.write_text("bin/\nobj/\n", encoding="utf-8")
            ok, error = validate_workspace_gitignore(tmpdir)
        self.assertFalse(ok)
        self.assertIn(".orc/", error)


if __name__ == "__main__":
    unittest.main()
