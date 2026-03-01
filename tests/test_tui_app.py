#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.backlog_status import BacklogStatus
from orc_core.tui_app import OrcApp
from orc_core.tui_app import run_start_menu


class OrcAppErrorReportingTest(unittest.TestCase):
    def test_background_runner_keeps_exception_text(self) -> None:
        def broken() -> int:
            raise RuntimeError("boom")

        app = OrcApp(broken)
        app.call_from_thread = lambda callback, *args: callback(*args)  # type: ignore[assignment]

        app._run_in_background()

        self.assertIsNotNone(app.last_error)
        self.assertIn("RuntimeError: boom", app.last_error or "")


class TuiMouseReportingTest(unittest.TestCase):
    def test_run_start_menu_disables_mouse_reporting(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        with patch("orc_core.tui_app._StartMenuApp.run", return_value=None) as run_mock:
            run_start_menu(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        run_mock.assert_called_once_with(mouse=False)


if __name__ == "__main__":
    unittest.main()
