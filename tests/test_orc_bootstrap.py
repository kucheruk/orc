#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import MagicMock, patch

import orc


class OrcBootstrapTest(unittest.TestCase):
    @patch("orc.subprocess.Popen")
    def test_run_from_orc_project_returns_130_on_keyboard_interrupt(self, popen_mock) -> None:
        proc = MagicMock()
        proc.wait.side_effect = [KeyboardInterrupt, None]
        proc.poll.return_value = None
        popen_mock.return_value = proc
        rc = orc._run_from_orc_project()
        self.assertEqual(rc, 130)
        proc.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
