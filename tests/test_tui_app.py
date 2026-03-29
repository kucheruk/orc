#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from orc_core.backlog_status import BacklogStatus
from orc_core.stream_monitor_state import MetricsStore, MonitorSnapshot
from orc_core.tui.messages import OrchestratorFinished, SnapshotUpdated
from orc_core.tui_app import OrcApp
from orc_core.tui_app import run_start_menu


class OrcAppMessageHandlingTest(unittest.TestCase):
    def _make_snapshot(self) -> MonitorSnapshot:
        return MonitorSnapshot(
            task_id="TASK-1",
            started_at=1.0,
            progress_done=1,
            progress_total=2,
            metrics=MetricsStore(tokens_total=10, files_edited=1, command_count=2, total_lines=3, total_output_chars=20),
            last_event_type="assistant",
            last_event_note="thinking",
            recent_commands=["ReadFile"],
            recent_files=["/tmp/file.py"],
            recent_events=["assistant:thinking"],
            reasoning_lines=["planning"],
            spinner_idx=0,
            last_event_at=2.0,
        )

    def test_snapshot_message_updates_execution_screen(self) -> None:
        app = OrcApp(lambda _publish: 0)
        app._execution_screen.update_session = MagicMock()

        app.on_snapshot_updated(SnapshotUpdated("session-1", self._make_snapshot()))

        app._execution_screen.update_session.assert_called_once()

    def test_orchestrator_finished_stores_error_and_exits(self) -> None:
        app = OrcApp(lambda _publish: 0)
        app.exit = MagicMock()

        app.on_orchestrator_finished(OrchestratorFinished(exit_code=7, error_text="traceback"))

        self.assertEqual(app.last_error, "traceback")
        app.exit.assert_called_once_with(1)


class TuiMouseReportingTest(unittest.TestCase):
    def test_run_start_menu_disables_mouse_reporting(self) -> None:
        status = BacklogStatus(path=Path("BACKLOG.md"), exists=True, tasks=[], open_tasks=[])
        with patch("orc_core.tui_app._StartMenuApp.run", return_value=None) as run_mock:
            run_start_menu(status, models=["gpt-5.3-codex"], default_model="gpt-5.3-codex")

        run_mock.assert_called_once_with(mouse=False)


if __name__ == "__main__":
    unittest.main()
