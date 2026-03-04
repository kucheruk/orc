#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from orc_core.stream_monitor import StreamJsonMonitor


class StreamMonitorMetricsAtomicWriteTest(unittest.TestCase):
    def test_write_metrics_snapshot_uses_atomic_json_writer(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor.task_id = "TASK-ATOMIC"
        monitor.log_path = Path("/tmp/orc.log")
        monitor.metrics = SimpleNamespace(
            tokens_total=123,
            total_lines=7,
            command_count=2,
            files_edited=1,
            git_added=10,
            git_deleted=3,
            tokens_status="known",
            tokens_source="structured",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor.workdir = tmpdir
            expected_path = Path(tmpdir) / ".orc" / "orc-metrics.json"
            with patch("orc_core.stream_monitor.write_json_atomic") as write_json_atomic_mock:
                monitor._write_metrics_snapshot()

        write_json_atomic_mock.assert_called_once()
        called_path = write_json_atomic_mock.call_args.args[0]
        self.assertEqual(called_path, expected_path)


if __name__ == "__main__":
    unittest.main()
