#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.git import worktree_flow


class WorktreeFlowTest(unittest.TestCase):
    @patch("orc_core.git.worktree_flow.run_git")
    def test_resolve_integration_commit_skips_tasks_only_commit(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "aaa111\nbbb222\n", "", 0),  # rev-list --no-merges main..HEAD
            (True, "tasks/5_Review/UX-001.md\n", "", 0),  # show aaa111 files
            (True, "src/Jeeves.Web/Program.cs\n", "", 0),  # show bbb222 files
        ]
        commit = worktree_flow.resolve_integration_commit("/tmp/repo", "master")
        self.assertEqual(commit, "bbb222")

    @patch("orc_core.git.worktree_flow.run_git")
    def test_resolve_integration_commit_fails_when_only_tasks_commits(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "aaa111\n", "", 0),  # rev-list --no-merges main..HEAD
            (True, "tasks/8_Done/UX-001.md\n", "", 0),  # show aaa111 files
        ]
        with self.assertRaises(RuntimeError):
            worktree_flow.resolve_integration_commit("/tmp/repo", "master")

    @patch("orc_core.git.worktree_flow.run_git")
    def test_detect_base_branch_prefers_main_when_exists(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "refs/heads/main\n", "", 0),
        ]
        branch = worktree_flow.detect_base_branch("/tmp/repo")
        self.assertEqual(branch, "main")

    @patch("orc_core.git.worktree_flow.run_git")
    def test_detect_base_branch_falls_back_to_master(self, git_mock) -> None:
        git_mock.side_effect = [
            (False, "", "fatal: bad revision", 128),
            (True, "refs/heads/master\n", "", 0),
        ]
        branch = worktree_flow.detect_base_branch("/tmp/repo")
        self.assertEqual(branch, "master")

    @patch("orc_core.git.worktree_flow.run_git")
    def test_cherry_pick_detects_conflict_by_unmerged_files(self, git_mock) -> None:
        git_mock.side_effect = [
            (False, "", "", 1),  # cherry-pick failed, no stderr hint
            (True, "conflicted.py\n", "", 0),  # unmerged files exist
        ]
        ok, conflict, error = worktree_flow._cherry_pick_commit("/tmp/repo", "abc123")
        self.assertFalse(ok)
        self.assertTrue(conflict)
        self.assertEqual(error, "")

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_fails_when_base_repo_dirty(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, " M tracked.py\n", "", 0),  # tracked status
            (True, "", "", 0),  # untracked list
        ]
        result = worktree_flow.integrate_commit_into_main(
            base_workdir="/tmp/repo",
            commit_sha="abc123",
            task_id="TASK-001",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("dirty", result.error)
        self.assertIn("tracked:tracked.py", result.error)

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_returns_already_integrated(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),  # tracked status clean
            (True, "", "", 0),  # untracked list
            (True, "", "", 0),  # show-ref main
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

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_ignores_runtime_untracked_before_integration(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),  # tracked status clean
            (
                True,
                ".cursor/hooks.json\n"
                ".cursor/hooks/orc_before_submit.py\n"
                ".cursor/hooks/orc_hook_lib.py\n"
                ".cursor/hooks/orc_stop.py\n"
                ".cursor/orc-stop-request.json\n"
                ".orc/run/raw-stream/task.log\n",
                "",
                0,
            ),
            (True, "", "", 0),  # show-ref main
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

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_fails_when_non_runtime_untracked_exists(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),  # tracked status clean
            (True, "notes.txt\n", "", 0),  # untracked list
        ]
        result = worktree_flow.integrate_commit_into_main(
            base_workdir="/tmp/repo",
            commit_sha="abc123",
            task_id="TASK-001",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("dirty", result.error)
        self.assertIn("untracked:notes.txt", result.error)

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_ignores_runtime_tracked_before_integration(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, " M .cursor/orc-stop-request.json\n", "", 0),  # tracked runtime artifact
            (True, "", "", 0),  # untracked list clean
            (True, "", "", 0),  # show-ref main
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

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_treats_empty_cherry_pick_as_already_integrated(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),  # tracked status clean
            (True, "", "", 0),  # untracked list clean
            (True, "", "", 0),  # show-ref main
            (True, "", "", 0),  # checkout main
            (False, "", "", 1),  # merge-base not ancestor
            (
                False,
                "",
                "The previous cherry-pick is now empty, possibly due to conflict resolution.",
                1,
            ),  # cherry-pick stderr
            (True, "", "", 0),  # diff conflicts check
        ]
        result = worktree_flow.integrate_commit_into_main(
            base_workdir="/tmp/repo",
            commit_sha="abc123",
            task_id="TASK-001",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.already_integrated)

    @patch("orc_core.git.worktree_flow.run_git")
    def test_integrate_commit_handles_collapsed_cursor_status_entry(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "?? .cursor/\n", "", 0),  # tracked status (unexpected collapsed entry)
            (True, ".cursor/orc-stop-request.json\n.orc/run/raw-stream/task.log\n", "", 0),  # untracked expanded
            (True, "", "", 0),  # show-ref main
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

    @patch("orc_core.git.worktree_flow.run_git")
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
            (True, "", "", 0),  # branch -D
        ]

        worktree_flow.cleanup_task_worktree(session, Path("/tmp/orc.log"))

        self.assertEqual(
            git_mock.call_args_list[2].args[1],
            ["git", "worktree", "remove", "--force", session.worktree_path],
        )

    @patch("orc_core.git.worktree_flow.run_git")
    def test_cleanup_worktree_force_removes_when_only_cursor_runtime_dirty(self, git_mock) -> None:
        session = worktree_flow.WorktreeSession(
            base_workdir="/tmp/repo",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
        )
        git_mock.side_effect = [
            (False, "", "contains modified files", 128),  # regular remove failed
            (True, "?? .cursor/orc-stop-request.json\n?? .orc/some-file.log\n", "", 0),  # status in worktree
            (True, "", "", 0),  # force remove succeeded
            (True, "", "", 0),  # prune
            (True, "", "", 0),  # branch -D
        ]

        worktree_flow.cleanup_task_worktree(session, Path("/tmp/orc.log"))

        self.assertEqual(
            git_mock.call_args_list[2].args[1],
            ["git", "worktree", "remove", "--force", session.worktree_path],
        )

    @patch("orc_core.git.worktree_flow.run_git")
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


class MergeTaskBranchTest(unittest.TestCase):
    @patch("os.path.isdir", return_value=False)
    @patch("orc_core.git.worktree_flow.log_event")
    @patch("orc_core.git.worktree_flow.run_git")
    def test_merge_succeeds_with_squash(self, git_mock, _log_mock, _isdir_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),   # tracked status clean
            (True, "", "", 0),   # untracked list clean
            (True, "", "", 0),   # show-ref main
            (True, "", "", 0),   # checkout main
            (True, "", "", 0),   # show-ref branch
            (True, "abc123\n", "", 0),  # merge-base
            (True, "src/app.py\n", "", 0),  # diff merge-base..branch (files changed)
            (True, "some diff\n", "", 0),  # diff branch main (content differs)
            (True, "", "", 0),   # merge --squash
            (True, "", "", 0),   # commit
        ]
        result = worktree_flow.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertTrue(result.ok)
        self.assertFalse(result.conflict)
        # Verify squash merge was called
        merge_call = git_mock.call_args_list[8]
        self.assertEqual(merge_call.args[1], ["git", "merge", "--squash", "orc/TASK-001"])

    @patch("orc_core.git.worktree_flow.run_git")
    def test_merge_returns_already_integrated_when_no_diff(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),   # tracked status clean
            (True, "", "", 0),   # untracked list clean
            (True, "", "", 0),   # show-ref main
            (True, "", "", 0),   # checkout main
            (True, "", "", 0),   # show-ref branch
            (True, "abc123\n", "", 0),  # merge-base
            (True, "src/app.py\n", "", 0),  # diff merge-base..branch (files changed)
            (True, "", "", 0),   # diff branch main (content identical = integrated)
        ]
        result = worktree_flow.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.already_integrated)

    @patch("os.path.isdir", return_value=False)
    @patch("orc_core.git.worktree_flow.log_event")
    @patch("orc_core.git.worktree_flow.run_git")
    def test_merge_detects_conflict(self, git_mock, _log_mock, _isdir_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),   # tracked status clean
            (True, "", "", 0),   # untracked list clean
            (True, "", "", 0),   # show-ref main
            (True, "", "", 0),   # checkout main
            (True, "", "", 0),   # show-ref branch
            (True, "abc123\n", "", 0),  # merge-base
            (True, "src/app.py\n", "", 0),  # diff merge-base..branch
            (True, "some diff\n", "", 0),  # diff branch main (not integrated)
            (False, "", "CONFLICT (content): Merge conflict in src/app.py", 1),  # merge --squash
            (True, "src/app.py\n", "", 0),  # diff --name-only --diff-filter=U (unmerged)
        ]
        result = worktree_flow.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.conflict)

    @patch("os.path.isdir", return_value=False)
    @patch("orc_core.git.worktree_flow.log_event")
    @patch("orc_core.git.worktree_flow.run_git")
    def test_merge_fails_when_branch_not_found(self, git_mock, _log_mock, _isdir_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),   # tracked status clean
            (True, "", "", 0),   # untracked list clean
            (True, "", "", 0),   # show-ref main
            (True, "", "", 0),   # checkout main
            (False, "", "not found", 1),  # show-ref branch fails
        ]
        result = worktree_flow.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("not found", result.error)

    @patch("orc_core.git.worktree_flow.run_git")
    def test_merge_fails_when_base_repo_dirty(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, " M tracked.py\n", "", 0),  # tracked status dirty
            (True, "", "", 0),                   # untracked list
        ]
        result = worktree_flow.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("dirty", result.error)

    @patch("orc_core.git.worktree_flow.run_git")
    def test_abort_merge_uses_reset(self, git_mock) -> None:
        git_mock.return_value = (True, "", "", 0)
        ok = worktree_flow.abort_merge("/tmp/repo")
        self.assertTrue(ok)
        git_mock.assert_called_once_with("/tmp/repo", ["git", "reset", "--merge"])


if __name__ == "__main__":
    unittest.main()
