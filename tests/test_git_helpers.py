#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from orc_core.git import git_helpers
from orc_core.errors.failure_reasons import IntegrationErrorKind


class GitStatusPorcelainTest(unittest.TestCase):
    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_returns_stdout_on_success(self, run_mock) -> None:
        run_mock.return_value = MagicMock(returncode=0, stdout=" M file.py\n?? new.py\n", stderr="")
        ok, output = git_helpers.git_status_porcelain("/tmp/repo", Path("/tmp/orc.log"))
        self.assertTrue(ok)
        self.assertIn("file.py", output)

    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_returns_false_on_nonzero_exit(self, run_mock) -> None:
        run_mock.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a repo")
        ok, output = git_helpers.git_status_porcelain("/tmp/repo", Path("/tmp/orc.log"))
        self.assertFalse(ok)
        self.assertEqual(output, "")

    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_returns_false_on_timeout(self, run_mock) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=20)
        ok, output = git_helpers.git_status_porcelain("/tmp/repo", Path("/tmp/orc.log"))
        self.assertFalse(ok)

    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_returns_false_on_exception(self, run_mock) -> None:
        run_mock.side_effect = OSError("disk error")
        ok, output = git_helpers.git_status_porcelain("/tmp/repo", Path("/tmp/orc.log"))
        self.assertFalse(ok)


class ParseGitPorcelainTest(unittest.TestCase):
    def test_separates_tracked_and_untracked(self) -> None:
        porcelain = " M src/app.py\n?? new_file.txt\nA  added.py\n"
        tracked, untracked = git_helpers.parse_git_porcelain(porcelain)
        self.assertEqual(tracked, ["src/app.py", "added.py"])
        self.assertEqual(untracked, ["new_file.txt"])

    def test_empty_input(self) -> None:
        tracked, untracked = git_helpers.parse_git_porcelain("")
        self.assertEqual(tracked, [])
        self.assertEqual(untracked, [])

    def test_none_input(self) -> None:
        tracked, untracked = git_helpers.parse_git_porcelain(None)
        self.assertEqual(tracked, [])
        self.assertEqual(untracked, [])


class IsRuntimeArtifactTest(unittest.TestCase):
    def test_orc_dir_is_artifact(self) -> None:
        self.assertTrue(git_helpers.is_runtime_artifact(".orc/task.json"))

    def test_cursor_dir_is_artifact(self) -> None:
        self.assertTrue(git_helpers.is_runtime_artifact(".cursor/settings.json"))

    def test_pycache_is_artifact(self) -> None:
        self.assertTrue(git_helpers.is_runtime_artifact("src/__pycache__/mod.pyc"))

    def test_nohup_is_artifact(self) -> None:
        self.assertTrue(git_helpers.is_runtime_artifact("nohup.out"))

    def test_regular_file_is_not_artifact(self) -> None:
        self.assertFalse(git_helpers.is_runtime_artifact("src/main.py"))

    def test_empty_string(self) -> None:
        self.assertFalse(git_helpers.is_runtime_artifact(""))


class GitRunTest(unittest.TestCase):
    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_success_returns_ok_and_output(self, run_mock) -> None:
        run_mock.return_value = MagicMock(returncode=0, stdout="abc123\n", stderr="")
        ok, stdout, stderr, rc = git_helpers.git_run("/tmp", Path("/tmp/orc.log"), ["git", "rev-parse", "HEAD"], "test")
        self.assertTrue(ok)
        self.assertEqual(stdout, "abc123\n")
        self.assertEqual(rc, 0)

    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_failure_returns_not_ok(self, run_mock) -> None:
        run_mock.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        ok, stdout, stderr, rc = git_helpers.git_run("/tmp", Path("/tmp/orc.log"), ["git", "status"], "test")
        self.assertFalse(ok)
        self.assertEqual(rc, 1)

    @patch("orc_core.git.subprocess_git.subprocess.run")
    def test_timeout_returns_code_124(self, run_mock) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=20)
        ok, stdout, stderr, rc = git_helpers.git_run("/tmp", Path("/tmp/orc.log"), ["git", "status"], "test")
        self.assertFalse(ok)
        self.assertEqual(rc, 124)
        self.assertEqual(stderr, "timeout")


class HasCommitsAheadTest(unittest.TestCase):
    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_true_when_commits_ahead(self, git_mock) -> None:
        git_mock.return_value = (True, "3\n", "", 0)
        self.assertTrue(git_helpers.has_commits_ahead_of_branch("/tmp", "main", Path("/tmp/orc.log")))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_false_when_zero_ahead(self, git_mock) -> None:
        git_mock.return_value = (True, "0\n", "", 0)
        self.assertFalse(git_helpers.has_commits_ahead_of_branch("/tmp", "main", Path("/tmp/orc.log")))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_false_on_failure(self, git_mock) -> None:
        git_mock.return_value = (False, "", "error", 1)
        self.assertFalse(git_helpers.has_commits_ahead_of_branch("/tmp", "main", Path("/tmp/orc.log")))


class HasCodeChangesAheadTest(unittest.TestCase):
    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_true_when_code_files_changed(self, git_mock) -> None:
        git_mock.return_value = (True, "src/App.cs\nsrc/Program.cs\n", "", 0)
        self.assertTrue(git_helpers.has_code_changes_ahead("/tmp", "main", Path("/tmp/orc.log")))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_false_when_only_empty_output(self, git_mock) -> None:
        git_mock.return_value = (True, "\n", "", 0)
        self.assertFalse(git_helpers.has_code_changes_ahead("/tmp", "main", Path("/tmp/orc.log")))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_false_when_no_output(self, git_mock) -> None:
        git_mock.return_value = (True, "", "", 0)
        self.assertFalse(git_helpers.has_code_changes_ahead("/tmp", "main", Path("/tmp/orc.log")))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_false_on_failure(self, git_mock) -> None:
        git_mock.return_value = (False, "", "error", 1)
        self.assertFalse(git_helpers.has_code_changes_ahead("/tmp", "main", Path("/tmp/orc.log")))

    @patch("orc_core.git.git_helpers.git_run")
    def test_excludes_tasks_dir_via_pathspec(self, git_mock) -> None:
        git_mock.return_value = (True, "", "", 0)
        git_helpers.has_code_changes_ahead("/tmp", "main", Path("/tmp/orc.log"))
        args = git_mock.call_args[0]  # positional args to git_run
        cmd = args[2]  # the command list
        self.assertIn(":!tasks/", cmd)


class AutocommitFallbackTest(unittest.TestCase):
    @patch("orc_core.git.git_helpers.git_run")
    def test_succeeds_when_all_git_commands_pass(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),   # git add -A
            (False, "", "", 1),  # git diff --cached --quiet (changes exist)
            (True, "", "", 0),   # git commit
        ]
        self.assertTrue(git_helpers.attempt_autocommit_fallback("/tmp", Path("/tmp/orc.log"), "TASK-1", "Fix bug"))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_true_when_nothing_to_commit(self, git_mock) -> None:
        git_mock.side_effect = [
            (True, "", "", 0),   # git add -A
            (True, "", "", 0),   # git diff --cached --quiet (clean)
        ]
        self.assertTrue(git_helpers.attempt_autocommit_fallback("/tmp", Path("/tmp/orc.log"), "TASK-1", ""))

    @patch("orc_core.git.git_helpers.git_run")
    def test_returns_false_when_add_fails(self, git_mock) -> None:
        git_mock.return_value = (False, "", "error", 1)
        self.assertFalse(git_helpers.attempt_autocommit_fallback("/tmp", Path("/tmp/orc.log"), "TASK-1", ""))


class ClassifyMainIntegrationErrorTest(unittest.TestCase):
    def test_dirty_base_repo(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error("dirty before integration"),
            IntegrationErrorKind.DIRTY_BASE_REPO,
        )

    def test_git_status_failed(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error("git status failed: timeout"),
            IntegrationErrorKind.GIT_STATUS_FAILED,
        )

    def test_main_branch_missing(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error("main branch 'main' not found"),
            IntegrationErrorKind.MAIN_BRANCH_MISSING,
        )

    def test_timeout(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error("command timeout after 20s"),
            IntegrationErrorKind.GIT_TIMEOUT,
        )

    def test_cherry_pick_failed(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error("cherry-pick conflict"),
            IntegrationErrorKind.CHERRY_PICK_FAILED,
        )

    def test_empty_string(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error(""),
            IntegrationErrorKind.UNKNOWN,
        )

    def test_unknown_error(self) -> None:
        self.assertEqual(
            git_helpers.classify_main_integration_error("something unexpected"),
            IntegrationErrorKind.UNKNOWN,
        )


class RuntimeArtifactFilterTest(unittest.TestCase):
    def test_separates_runtime_from_non_runtime(self) -> None:
        paths = ["src/main.py", ".orc/task.json", "README.md", "__pycache__/mod.pyc"]
        runtime, non_runtime = git_helpers.runtime_artifact_paths_from_porcelain_lines(paths)
        self.assertEqual(runtime, [".orc/task.json", "__pycache__/mod.pyc"])
        self.assertEqual(non_runtime, ["src/main.py", "README.md"])
