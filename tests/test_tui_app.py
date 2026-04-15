#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import MagicMock

from orc_core.infra.monitoring.monitor_dto import MetricsStore, MonitorSnapshot
from orc_core.tui.messages import OrchestratorFinished, SnapshotUpdated
from orc_core.cli.tui_app import OrcApp


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

    def test_orchestrator_finished_stores_error_and_exits(self) -> None:
        app = OrcApp(lambda _publish: 0)
        app.exit = MagicMock()

        app.on_orchestrator_finished(OrchestratorFinished(exit_code=7, error_text="traceback"))

        self.assertEqual(app.last_error, "traceback")
        app.exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
