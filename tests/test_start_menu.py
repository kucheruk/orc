#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from orc_core.start_menu import _pick_debug_enabled


class StartMenuDebugOptionTest(unittest.TestCase):
    @patch("orc_core.start_menu.radiolist_dialog")
    def test_pick_debug_enabled_returns_true_when_selected(self, dialog_mock) -> None:
        dialog_mock.return_value.run.return_value = "on"
        self.assertTrue(_pick_debug_enabled())

    @patch("orc_core.start_menu.radiolist_dialog")
    def test_pick_debug_enabled_returns_false_by_default(self, dialog_mock) -> None:
        dialog_mock.return_value.run.return_value = "off"
        self.assertFalse(_pick_debug_enabled())

    @patch("orc_core.start_menu.radiolist_dialog")
    def test_pick_debug_enabled_treats_cancel_as_false(self, dialog_mock) -> None:
        dialog_mock.return_value.run.return_value = None
        self.assertFalse(_pick_debug_enabled())

if __name__ == "__main__":
    unittest.main()
