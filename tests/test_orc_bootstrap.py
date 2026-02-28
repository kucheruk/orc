#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

import orc


class OrcBootstrapTest(unittest.TestCase):
    @patch("orc.subprocess.call", side_effect=KeyboardInterrupt)
    def test_run_from_orc_project_returns_130_on_keyboard_interrupt(self, _subprocess_call) -> None:
        rc = orc._run_from_orc_project()
        self.assertEqual(rc, 130)


if __name__ == "__main__":
    unittest.main()
