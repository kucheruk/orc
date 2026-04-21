#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.git import branch_merger, branch_resolver, integration_preflight, worktree_lifecycle
from orc_core.git.git_dto import WorktreeSession


def _shared_side_effect(responses):
    """Build a side_effect function that drains a single shared queue.

    Used when we need to patch run_git in multiple modules but want the
    calls to consume responses in order regardless of which module makes
    the call.
    """
    it = iter(responses)

    def _fn(*args, **kwargs):
        return next(it)

    return _fn


class BranchResolverTest(unittest.TestCase):
    @patch("orc_core.git.branch_resolver.run_git")
    def test_resolve_integration_commit_skips_tasks_only_commit(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "aaa111\nbbb222\n", "", 0),  # rev-list --no-merges main..HEAD
            (True, "tasks/5_Review/UX-001.md\n", "", 0),  # show aaa111 files
            (True, "src/Jeeves.Web/Program.cs\n", "", 0),  # show bbb222 files
        ]
        commit = branch_resolver.resolve_integration_commit("/tmp/repo", "master")
        self.assertEqual(commit, "bbb222")

    @patch("orc_core.git.branch_resolver.run_git")
    def test_resolve_integration_commit_fails_when_only_tasks_commits(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "aaa111\n", "", 0),
            (True, "tasks/8_Done/UX-001.md\n", "", 0),
        ]
        with self.assertRaises(RuntimeError):
            branch_resolver.resolve_integration_commit("/tmp/repo", "master")

    @patch("orc_core.git.branch_resolver.run_git")
    def test_detect_base_branch_prefers_main_when_exists(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "refs/heads/main\n", "", 0),
        ]
        self.assertEqual(branch_resolver.detect_base_branch("/tmp/repo"), "main")

    @patch("orc_core.git.branch_resolver.run_git")
    def test_detect_base_branch_falls_back_to_master(self, git_mock) -> None:
        git_mock.side_effect = [
            (False, "", "fatal: bad revision", 128),
            (True, "refs/heads/master\n", "", 0),
        ]
        self.assertEqual(branch_resolver.detect_base_branch("/tmp/repo"), "master")


class WorktreeLifecycleTest(unittest.TestCase):
    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("orc_core.git.worktree_lifecycle.run_git")
    def test_create_task_worktree_does_not_reset_existing_branch(
        self, git_mock, _exists_mock, _write_text_mock,
    ) -> None:
        git_mock.side_effect = [
            # First worktree add attempt — fails because branch already exists.
            (False, "", "branch already exists", 128),
            # Reattach as existing branch succeeds.
            (True, "", "", 0),
            # _apply_worktree_merge_attributes: rev-parse, config ours name, config ours driver.
            (True, ".git/worktrees/TASK-001", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
        ]

        session = worktree_lifecycle.create_task_worktree(
            base_workdir="/tmp/repo",
            task_id="TASK-001",
            log_path=Path("/tmp/orc.log"),
            main_branch="master",
        )

        self.assertEqual(session.branch_name, "orc/TASK-001")
        # Two worktree-add calls + three attribute-setup calls.
        self.assertEqual(len(git_mock.call_args_list), 5)
        self.assertEqual(
            git_mock.call_args_list[0],
            unittest.mock.call(
                "/tmp/repo",
                ["git", "worktree", "add", "-b", "orc/TASK-001", session.worktree_path, "master"],
            ),
        )
        self.assertEqual(
            git_mock.call_args_list[1],
            unittest.mock.call(
                "/tmp/repo",
                ["git", "worktree", "add", session.worktree_path, "orc/TASK-001"],
            ),
        )
        # Attribute-setup must target the new worktree path, not the base repo.
        self.assertEqual(git_mock.call_args_list[2].args[0], session.worktree_path)
        self.assertEqual(git_mock.call_args_list[2].args[1], ["git", "rev-parse", "--git-dir"])
        self.assertIn("merge.ours.driver", git_mock.call_args_list[4].args[1])

    def test_worktree_merge_attributes_file_is_written(self) -> None:
        """Integration test: the per-worktree info/attributes file must
        contain the `tasks/** merge=ours` line after create_task_worktree
        so agent-driven `git merge master` resolves cleanly instead of
        leaving `<<<<<<<` markers in card files (jeeves NOTIF-003-C
        2026-04-21: 5 bouncebacks on the same conflict-marker issue)."""
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_repo:
            def run(*argv: str) -> None:
                subprocess.run(argv, cwd=tmp_repo, check=True, capture_output=True)

            run("git", "init", "-q", "-b", "master")
            run("git", "-c", "user.email=t@t", "-c", "user.name=t", "commit",
                "--allow-empty", "-m", "initial", "-q")

            with patch(
                "orc_core.git.worktree_lifecycle.worktrees_root",
                return_value=Path(tmp_repo) / "_orc_worktrees",
            ):
                session = worktree_lifecycle.create_task_worktree(
                    base_workdir=tmp_repo,
                    task_id="TASK-MERGE",
                    log_path=Path("/tmp/orc-test.log"),
                    main_branch="master",
                )

            gitdir = Path(session.worktree_path) / ".git"
            # For linked worktrees `.git` is a file pointing to the real gitdir.
            real_gitdir_line = gitdir.read_text(encoding="utf-8").strip()
            self.assertTrue(real_gitdir_line.startswith("gitdir:"))
            real_gitdir = Path(real_gitdir_line.removeprefix("gitdir:").strip())
            attrs = (real_gitdir / "info" / "attributes").read_text(encoding="utf-8")
            self.assertIn("tasks/**", attrs)
            self.assertIn("merge=ours", attrs)

    @patch("orc_core.git.worktree_lifecycle.run_git")
    def test_cleanup_worktree_force_removes_when_only_orc_runtime_dirty(self, git_mock) -> None:
        session = WorktreeSession(
            base_workdir="/tmp/repo",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
        )
        git_mock.side_effect = [
            (False, "", "contains modified files", 128),
            (True, " M .orc/backlog-run/raw-stream/task.log\n", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
        ]

        worktree_lifecycle.cleanup_task_worktree(session, Path("/tmp/orc.log"))

        self.assertEqual(
            git_mock.call_args_list[2].args[1],
            ["git", "worktree", "remove", "--force", session.worktree_path],
        )

    @patch("orc_core.git.worktree_lifecycle.run_git")
    def test_cleanup_worktree_force_removes_when_only_cursor_runtime_dirty(self, git_mock) -> None:
        session = WorktreeSession(
            base_workdir="/tmp/repo",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
        )
        git_mock.side_effect = [
            (False, "", "contains modified files", 128),
            (True, "?? .cursor/orc-stop-request.json\n?? .orc/some-file.log\n", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
        ]

        worktree_lifecycle.cleanup_task_worktree(session, Path("/tmp/orc.log"))

        self.assertEqual(
            git_mock.call_args_list[2].args[1],
            ["git", "worktree", "remove", "--force", session.worktree_path],
        )

    @patch("orc_core.git.worktree_lifecycle.run_git")
    def test_cleanup_worktree_fails_when_dirty_paths_not_in_orc(self, git_mock) -> None:
        session = WorktreeSession(
            base_workdir="/tmp/repo",
            worktree_path="/tmp/repo/.orc/worktrees/TASK-001",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
        )
        git_mock.side_effect = [
            (False, "", "contains modified files", 128),
            (True, " M BACKLOG.md\n", "", 0),
        ]

        with self.assertRaises(RuntimeError):
            worktree_lifecycle.cleanup_task_worktree(session, Path("/tmp/orc.log"))


class MergeTaskBranchTest(unittest.TestCase):
    def _patch_cross_module_run_git(self, responses):
        shared = _shared_side_effect(responses)
        p1 = patch("orc_core.git.integration_preflight.run_git", side_effect=shared)
        p2 = patch("orc_core.git.branch_merger.run_git", side_effect=shared)
        p1.start()
        p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    @patch("os.path.isdir", return_value=False)
    @patch("orc_core.git.branch_merger.log_event")
    def test_merge_succeeds_with_squash(self, _log_mock, _isdir_mock) -> None:
        calls: list = []

        def _record(workdir, args, **kwargs):
            calls.append((workdir, args))
            idx = len(calls) - 1
            responses = [
                (True, "", "", 0),   # preflight: tracked status
                (True, "", "", 0),   # preflight: untracked list
                (True, "", "", 0),   # preflight: show-ref main
                (True, "", "", 0),   # checkout main
                (True, "", "", 0),   # show-ref branch
                (True, "abc123\n", "", 0),    # merge-base
                (True, "src/app.py\n", "", 0),   # diff merge-base..branch
                (True, "some diff\n", "", 0),    # diff branch main (not integrated)
                (True, "", "", 0),   # merge --squash
                (True, "", "", 0),   # commit
            ]
            return responses[idx]

        with patch("orc_core.git.integration_preflight.run_git", side_effect=_record), \
             patch("orc_core.git.branch_merger.run_git", side_effect=_record):
            result = branch_merger.merge_task_branch_into_main(
                base_workdir="/tmp/repo",
                branch_name="orc/TASK-001",
                task_id="TASK-001",
                task_title="Fix auth bug",
                log_path=Path("/tmp/orc.log"),
            )
        self.assertTrue(result.ok)
        self.assertFalse(result.conflict)
        self.assertEqual(calls[8][1], ["git", "merge", "--squash", "orc/TASK-001"])

    def test_merge_returns_already_integrated_when_no_diff(self) -> None:
        self._patch_cross_module_run_git([
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "abc123\n", "", 0),
            (True, "src/app.py\n", "", 0),
            (True, "", "", 0),
        ])
        result = branch_merger.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.already_integrated)

    @patch("os.path.isdir", return_value=False)
    @patch("orc_core.git.branch_merger.log_event")
    def test_merge_detects_conflict(self, _log_mock, _isdir_mock) -> None:
        self._patch_cross_module_run_git([
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "abc123\n", "", 0),
            (True, "src/app.py\n", "", 0),
            (True, "some diff\n", "", 0),
            (False, "", "CONFLICT (content): Merge conflict in src/app.py", 1),
            (True, "src/app.py\n", "", 0),
            # Extra call: post-conflict listing for tasks-only auto-resolve
            # decision. src/app.py is outside tasks/, so the branch bails
            # to conflict=True as before.
            (True, "src/app.py\n", "", 0),
        ])
        result = branch_merger.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.conflict)

    @patch("os.path.isdir", return_value=False)
    @patch("orc_core.git.branch_merger.log_event")
    def test_merge_fails_when_branch_not_found(self, _log_mock, _isdir_mock) -> None:
        self._patch_cross_module_run_git([
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (True, "", "", 0),
            (False, "", "not found", 1),
        ])
        result = branch_merger.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("not found", result.error)

    def test_merge_fails_when_base_repo_dirty(self) -> None:
        self._patch_cross_module_run_git([
            (True, " M tracked.py\n", "", 0),
            (True, "", "", 0),
        ])
        result = branch_merger.merge_task_branch_into_main(
            base_workdir="/tmp/repo",
            branch_name="orc/TASK-001",
            task_id="TASK-001",
            task_title="Fix auth bug",
            log_path=Path("/tmp/orc.log"),
        )
        self.assertFalse(result.ok)
        self.assertIn("dirty", result.error)

    @patch("orc_core.git.branch_merger.run_git")
    def test_abort_merge_uses_reset(self, git_mock) -> None:
        git_mock.return_value = (True, "", "", 0)
        ok = branch_merger.abort_merge("/tmp/repo")
        self.assertTrue(ok)
        git_mock.assert_called_once_with("/tmp/repo", ["git", "reset", "--merge"])


class IntegrationPreflightTest(unittest.TestCase):
    @patch("orc_core.git.integration_preflight.run_git")
    def test_preflight_returns_error_when_dirty(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, " M tracked.py\n", "", 0),
            (True, "", "", 0),
        ]
        result = integration_preflight.preflight_main_integration(
            base_workdir="/tmp/repo", main_branch="main",
        )
        self.assertFalse(result.ok)
        self.assertIn("dirty", result.error)


if __name__ == "__main__":
    unittest.main()
