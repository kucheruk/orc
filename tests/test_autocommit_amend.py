#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AutoCommitStep amends consecutive unpushed auto-commits into one rolling commit."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from orc_core.agents.runners.teamlead_steps import AutoCommitStep


def _make_git(head_message: str, *, unpushed: bool, upstream_present: bool = True):
    """Minimal git-port stub recording the last commit/amend call."""
    calls: list[tuple[str, ...]] = []
    BOARD = "chore(board): update card positions"
    SYNC = "chore: sync board state and project files"

    def run(wd, argv):
        calls.append(tuple(argv))
        if argv[:3] == ["git", "log", "-1"]:
            return True, head_message, "", 0
        if argv[:3] == ["git", "rev-list", "@{upstream}..HEAD"]:
            if not upstream_present:
                return False, "", "fatal: no upstream configured", 128
            return True, ("abc\n" if unpushed else ""), "", 0
        # Record commit / amend; return success
        return True, "", "", 0

    git = SimpleNamespace(
        run=run,
        board_commit_message=lambda: BOARD,
        sync_commit_message=lambda: SYNC,
        calls=calls,
    )
    return git


def _ctx():
    return SimpleNamespace(log_path="ignored")


class AutoCommitAmendTest(unittest.TestCase):
    BOARD_MSG = "chore(board): update card positions"
    SYNC_MSG = "chore: sync board state and project files"

    def test_amends_when_head_is_unpushed_board_chore(self) -> None:
        git = _make_git(self.BOARD_MSG, unpushed=True)

        AutoCommitStep._commit_or_amend("/w", git, _ctx(), self.BOARD_MSG)

        commit_calls = [c for c in git.calls if c[:2] == ("git", "commit")]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("--amend", commit_calls[0])
        self.assertIn("--no-edit", commit_calls[0])
        self.assertNotIn("-m", commit_calls[0])

    def test_amends_when_head_is_unpushed_sync_chore(self) -> None:
        git = _make_git(self.SYNC_MSG, unpushed=True)

        AutoCommitStep._commit_or_amend("/w", git, _ctx(), self.SYNC_MSG)

        commit_calls = [c for c in git.calls if c[:2] == ("git", "commit")]
        self.assertIn("--amend", commit_calls[0])

    def test_fresh_commit_when_head_is_a_feat(self) -> None:
        git = _make_git("feat(X): ship something", unpushed=True)

        AutoCommitStep._commit_or_amend("/w", git, _ctx(), self.BOARD_MSG)

        commit_calls = [c for c in git.calls if c[:2] == ("git", "commit")]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("-m", commit_calls[0])
        self.assertIn(self.BOARD_MSG, commit_calls[0])
        self.assertNotIn("--amend", commit_calls[0])

    def test_fresh_commit_when_head_already_pushed(self) -> None:
        """Never amend a pushed commit — that would need force-push."""
        git = _make_git(self.BOARD_MSG, unpushed=False)

        AutoCommitStep._commit_or_amend("/w", git, _ctx(), self.BOARD_MSG)

        commit_calls = [c for c in git.calls if c[:2] == ("git", "commit")]
        self.assertIn("-m", commit_calls[0])
        self.assertNotIn("--amend", commit_calls[0])

    def test_fresh_commit_when_no_upstream_configured(self) -> None:
        """Missing upstream ⇒ can't know pushed-state, so default to fresh commit."""
        git = _make_git(self.BOARD_MSG, unpushed=True, upstream_present=False)

        AutoCommitStep._commit_or_amend("/w", git, _ctx(), self.BOARD_MSG)

        commit_calls = [c for c in git.calls if c[:2] == ("git", "commit")]
        self.assertIn("-m", commit_calls[0])
        self.assertNotIn("--amend", commit_calls[0])


if __name__ == "__main__":
    unittest.main()
