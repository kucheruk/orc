#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from orc_core.git.integration_manager import IntegrationContext, IntegrationManager
from orc_core.infra.session_types import SessionSlot, SlotStatus
from orc_core.tasks.task_source import Task


def _make_slot(sid: str = "s1") -> SessionSlot:
    return SessionSlot(session_id=sid, status=SlotStatus.RUNNING, thread=None)


def _make_task(tid: str = "TASK-1") -> Task:
    return Task(task_id=tid, text="Fix bug", done=False)


class IntegrationContextTest(unittest.TestCase):
    def test_report_tracks_steps(self) -> None:
        ctx = IntegrationContext(
            session_id="s1", task_id="T-1", workdir="/tmp",
            main_branch="main", log_path=Path("/tmp/orc.log"),
        )
        ctx.step("preflight", ok=True)
        ctx.step("cherry_pick", sha="abc123")
        self.assertEqual(len(ctx.report["steps"]), 2)
        self.assertEqual(ctx.report["steps"][0]["step"], "preflight")
        self.assertEqual(ctx.report["steps"][1]["sha"], "abc123")

    def test_step_error_marks_error(self) -> None:
        ctx = IntegrationContext(
            session_id="s1", task_id="T-1", workdir="/tmp",
            main_branch="main", log_path=Path("/tmp/orc.log"),
        )
        ctx.step_error("failed_step", reason="conflict")
        self.assertTrue(ctx.report["steps"][0]["error"])


class IntegrationManagerLockTest(unittest.TestCase):
    @patch("orc_core.git.integration_manager.IntegrationManager._execute")
    def test_integrate_acquires_lock(self, exec_mock) -> None:
        exec_mock.return_value = True
        mgr = IntegrationManager(workdir="/tmp", main_branch="main", log_path=Path("/tmp/orc.log"))
        result = mgr.integrate(_make_slot(), _make_task(), "/tmp/wt")
        self.assertTrue(result)
        exec_mock.assert_called_once()

    @patch("orc_core.git.integration_manager.IntegrationManager._execute")
    def test_integrate_catches_exception(self, exec_mock) -> None:
        exec_mock.side_effect = RuntimeError("boom")
        mgr = IntegrationManager(workdir="/tmp", main_branch="main", log_path=Path("/tmp/orc.log"))
        with patch.object(mgr, "_abort_cherry_pick"):
            result = mgr.integrate(_make_slot(), _make_task(), "/tmp/wt")
        self.assertFalse(result)


class RecoverStaleGitStateTest(unittest.TestCase):
    @patch("orc_core.git.integration_manager.run_git")
    def test_no_abort_when_no_marker_files(self, git_mock) -> None:
        git_mock.return_value = (True, ".git\n", "", 0)  # rev-parse --git-dir
        mgr = IntegrationManager(workdir="/tmp", main_branch="main", log_path=Path("/tmp/orc.log"))
        mgr.recover_stale_git_state()
        # Only rev-parse call, no abort calls because marker files don't exist
        self.assertEqual(git_mock.call_count, 1)
