#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core import worktree_flow


class WorktreeFlowTest(unittest.TestCase):
    @patch("orc_core.worktree_flow._git")
    def test_detect_base_branch_prefers_main_when_exists(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "refs/heads/main\n", "", 0),
        ]
        branch = worktree_flow.detect_base_branch("/tmp/repo")
        self.assertEqual(branch, "main")

    @patch("orc_core.worktree_flow._git")
    def test_detect_base_branch_falls_back_to_master(self, git_mock) -> None:
        git_mock.side_effect = [
            (False, "", "fatal: bad revision", 128),
            (True, "refs/heads/master\n", "", 0),
        ]
        branch = worktree_flow.detect_base_branch("/tmp/repo")
        self.assertEqual(branch, "master")

    @patch("orc_core.worktree_flow._git")
    def test_cherry_pick_detects_conflict_by_unmerged_files(self, git_mock) -> None:
        git_mock.side_effect = [
            (False, "", "", 1),  # cherry-pick failed, no stderr hint
            (True, "conflicted.py\n", "", 0),  # unmerged files exist
        ]
        ok, conflict, error = worktree_flow._cherry_pick_commit("/tmp/repo", "abc123")
        self.assertFalse(ok)
        self.assertTrue(conflict)
        self.assertEqual(error, "")

    @patch("orc_core.worktree_flow._git")
    def test_integrate_commit_fails_when_base_repo_dirty(self, git_mock) -> None:
        git_mock.return_value = (True, " M tracked.py\n", "", 0)
        result = worktree_flow.integrate_commit_into_main(
            base_workdir="/tmp/repo",
            commit_sha="abc123",
            task_id="TASK-001",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("dirty", result.error)

    @patch("orc_core.worktree_flow._git")
    def test_integrate_commit_returns_already_integrated(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),  # status clean
            (True, "", "", 0),  # checkout main
            (True, "", "", 0),  # merge-base --is-ancestor
        ]
        result = worktree_flow.integrate_commit_into_main(
            base_workdir="/tmp/repo",
            commit_sha="abc123",
            task_id="TASK-001",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.already_integrated)

    @patch("orc_core.worktree_flow._git")
    def test_cleanup_worktree_force_removes_when_only_orc_runtime_dirty(self, git_mock) -> None:
        session = worktree_flow.WorktreeSession(
            base_workdir="/tmp/repo",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
        )
        git_mock.side_effect = [
            (False, "", "contains modified files", 128),  # regular remove failed
            (True, " M .orc/backlog-run/raw-stream/task.log\n", "", 0),  # status in worktree
            (True, "", "", 0),  # force remove succeeded
            (True, "", "", 0),  # prune
        ]

        worktree_flow.cleanup_task_worktree(session, Path("/tmp/orc.log"))

        self.assertEqual(
            git_mock.call_args_list[2].args[1],
            ["git", "worktree", "remove", "--force", session.worktree_path],
        )

    @patch("orc_core.worktree_flow._git")
    def test_cleanup_worktree_fails_when_dirty_paths_not_in_orc(self, git_mock) -> None:
        session = worktree_flow.WorktreeSession(
            base_workdir="/tmp/repo",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
        )
        git_mock.side_effect = [
            (False, "", "contains modified files", 128),  # regular remove failed
            (True, " M BACKLOG.md\n", "", 0),  # status has non-runtime change
        ]

        with self.assertRaises(RuntimeError):
            worktree_flow.cleanup_task_worktree(session, Path("/tmp/orc.log"))


if __name__ == "__main__":
    unittest.main()
