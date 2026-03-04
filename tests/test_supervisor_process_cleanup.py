#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import orc_core.supervisor as supervisor


class SupervisorProcessCleanupTest(unittest.TestCase):
    def test_cleanup_prefers_process_group_then_orphan_sweep(self) -> None:
        monitor = SimpleNamespace(
            init_pid=None,
            proc=SimpleNamespace(pid=12345),
            process_group_id=4242,
            workdir="/tmp/project",
            started_at=100.0,
            run_token="run-token-supervisor",
        )
        with patch("orc_core.supervisor.terminate_process_group", return_value=True) as term_mock, patch(
            "orc_core.supervisor.kill_process_tree"
        ) as kill_tree_mock, patch(
            "orc_core.supervisor.kill_orphan_project_processes"
        ) as orphan_mock:
            supervisor._cleanup_monitor_processes(monitor, Path("/tmp/orc.log"), label="commit-phase")
        term_mock.assert_called_once_with(4242, Path("/tmp/orc.log"), label="commit-phase")
        kill_tree_mock.assert_not_called()
        orphan_mock.assert_called_once()
        self.assertEqual(orphan_mock.call_args.kwargs.get("run_token"), "run-token-supervisor")

    def test_cleanup_falls_back_to_process_tree_when_group_not_applied(self) -> None:
        monitor = SimpleNamespace(
            init_pid=None,
            proc=SimpleNamespace(pid=12345),
            process_group_id=4242,
            workdir="/tmp/project",
            started_at=100.0,
            run_token="run-token-supervisor",
        )
        with patch("orc_core.supervisor.terminate_process_group", return_value=False) as term_mock, patch(
            "orc_core.supervisor.kill_process_tree"
        ) as kill_tree_mock, patch(
            "orc_core.supervisor.kill_orphan_project_processes"
        ) as orphan_mock:
            supervisor._cleanup_monitor_processes(monitor, Path("/tmp/orc.log"), label="commit-phase")
        term_mock.assert_called_once_with(4242, Path("/tmp/orc.log"), label="commit-phase")
        kill_tree_mock.assert_called_once_with(12345, Path("/tmp/orc.log"), label="commit-phase")
        orphan_mock.assert_called_once()
        self.assertEqual(orphan_mock.call_args.kwargs.get("run_token"), "run-token-supervisor")


if __name__ == "__main__":
    unittest.main()
