#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import psutil

from orc_core.process_groups import subprocess_group_spawn_kwargs, terminate_process_group


class ProcessGroupsTest(unittest.TestCase):
    @patch("orc_core.process_groups.is_posix", return_value=True)
    def test_subprocess_group_spawn_kwargs_on_posix(self, _is_posix_mock) -> None:
        self.assertEqual(subprocess_group_spawn_kwargs(), {"start_new_session": True})

    @patch("orc_core.process_groups.is_posix", return_value=False)
    def test_subprocess_group_spawn_kwargs_on_non_posix(self, _is_posix_mock) -> None:
        self.assertEqual(subprocess_group_spawn_kwargs(), {})

    @patch("orc_core.process_groups.is_posix", return_value=True)
    @patch("orc_core.process_groups.psutil.wait_procs", return_value=([], []))
    @patch("orc_core.process_groups._group_processes")
    @patch("orc_core.process_groups.os.killpg")
    def test_terminate_process_group_term_path(self, killpg_mock, group_processes_mock, _wait_procs_mock, _is_posix_mock) -> None:
        member = Mock(spec=psutil.Process)
        member.pid = 123
        group_processes_mock.return_value = [member]
        applied = terminate_process_group(123, Path("/tmp/orc.log"), label="agent")
        self.assertTrue(applied)
        killpg_mock.assert_called_once()

    @patch("orc_core.process_groups.is_posix", return_value=True)
    @patch("orc_core.process_groups._group_processes", return_value=[])
    @patch("orc_core.process_groups.os.killpg", side_effect=ProcessLookupError)
    def test_terminate_process_group_handles_missing_group(self, _killpg_mock, _group_processes_mock, _is_posix_mock) -> None:
        applied = terminate_process_group(321, Path("/tmp/orc.log"), label="agent")
        self.assertTrue(applied)

    @patch("orc_core.process_groups.is_posix", return_value=True)
    @patch("orc_core.process_groups._group_processes", return_value=[])
    @patch("orc_core.process_groups.os.killpg", side_effect=PermissionError)
    def test_terminate_process_group_returns_false_on_permission_error(
        self, _killpg_mock, _group_processes_mock, _is_posix_mock
    ) -> None:
        applied = terminate_process_group(321, Path("/tmp/orc.log"), label="agent")
        self.assertFalse(applied)


if __name__ == "__main__":
    unittest.main()
