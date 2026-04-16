#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for conflict_resolver._try_auto_resolve — ensures the reconciler
only handles trivial cases and defers divergent conflicts to merge_expert."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orc_core.git.conflict_resolver import ConflictResolver


def _ours_theirs_file(tmpdir: Path, ours: str, theirs: str, *, name: str = "f.txt") -> Path:
    p = tmpdir / name
    p.write_text(
        "prefix\n"
        f"<<<<<<< HEAD\n{ours}=======\n{theirs}>>>>>>> branch\n"
        "suffix\n",
        encoding="utf-8",
    )
    return p


class _RunGitRecorder:
    """Records git calls and fakes their results deterministically."""

    def __init__(self, workdir: Path, conflict_files: list[str]):
        self.workdir = str(workdir)
        self.calls: list[list[str]] = []
        self._conflict_files = conflict_files
        self._commit_ok = True

    def __call__(self, workdir: str, args: list[str]):
        self.calls.append(list(args))
        if args[:3] == ["git", "diff", "--name-only"]:
            return True, "\n".join(self._conflict_files) + "\n", "", 0
        if args[:2] == ["git", "add"]:
            return True, "", "", 0
        if args[:3] == ["git", "commit", "--no-edit"]:
            return self._commit_ok, "", "" if self._commit_ok else "err", 0 if self._commit_ok else 1
        return True, "", "", 0


class AutoResolveTest(unittest.TestCase):
    def _run_with(self, conflict_files: dict[str, tuple[str, str]]):
        tmpdir = Path(tempfile.mkdtemp())
        for name, (ours, theirs) in conflict_files.items():
            _ours_theirs_file(tmpdir, ours, theirs, name=name)
        resolver = ConflictResolver(str(tmpdir))
        ctx = MagicMock()
        ctx.save_report = MagicMock()
        abort_fn = MagicMock()
        runner = _RunGitRecorder(tmpdir, list(conflict_files.keys()))
        with patch("orc_core.git.conflict_resolver.run_git", side_effect=runner):
            result = resolver._try_auto_resolve(ctx, abort_fn)
        return result, tmpdir, ctx, abort_fn, runner

    def test_empty_ours_keeps_theirs(self) -> None:
        # "ours is empty, theirs added stuff" → keep theirs
        result, tmpdir, _, _, _ = self._run_with({"a.py": ("", "added_line\n")})
        self.assertTrue(result)
        text = (tmpdir / "a.py").read_text()
        self.assertIn("added_line", text)
        self.assertNotIn("<<<<<<<", text)

    def test_empty_theirs_keeps_ours(self) -> None:
        result, tmpdir, _, _, _ = self._run_with({"a.py": ("our_line\n", "")})
        self.assertTrue(result)
        text = (tmpdir / "a.py").read_text()
        self.assertIn("our_line", text)
        self.assertNotIn("<<<<<<<", text)

    def test_identical_sides_keeps_one(self) -> None:
        result, tmpdir, _, _, _ = self._run_with({"a.py": ("same\n", "same\n")})
        self.assertTrue(result)
        text = (tmpdir / "a.py").read_text()
        self.assertEqual(text.count("same"), 1)
        self.assertNotIn("<<<<<<<", text)

    def test_divergent_content_defers_to_merge_expert(self) -> None:
        # Two real, different code changes — must NOT auto-concat; return None so
        # the caller falls through to the merge expert.
        result, tmpdir, ctx, abort_fn, _ = self._run_with(
            {"a.py": ("def f(): return 1\n", "def f(): return 2\n")}
        )
        self.assertIsNone(result)
        # File content must be left alone (conflict markers preserved) so the
        # merge expert sees the original conflict.
        text = (tmpdir / "a.py").read_text()
        self.assertIn("<<<<<<<", text)
        abort_fn.assert_not_called()

    def test_no_conflict_files_returns_none(self) -> None:
        result, _, _, _, _ = self._run_with({})
        self.assertIsNone(result)

    def test_multiple_files_one_divergent_defers_all(self) -> None:
        # Mixed: first file reconciles, second file diverges. Overall result
        # must be None (handoff to merge expert) so user-divergent changes
        # are not silently concatenated.
        result, tmpdir, _, abort_fn, _ = self._run_with({
            "a.py": ("", "clean_add\n"),
            "b.py": ("def x(): return 1\n", "def x(): return 2\n"),
        })
        self.assertIsNone(result)
        abort_fn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
