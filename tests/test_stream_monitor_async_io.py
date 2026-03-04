#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from orc_core.stream_monitor import StreamJsonMonitor


class StreamMonitorAsyncIoTest(unittest.IsolatedAsyncioTestCase):
    async def test_read_stdout_offloads_agent_output_write_to_thread(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor._stop = threading.Event()
        monitor._append_agent_output = MagicMock()
        monitor._record_event = MagicMock()
        monitor.log_path = Path("/tmp/orc.log")
        monitor.last_output_time = 0.0

        stream = asyncio.StreamReader()
        stream.feed_data(b'{"type":"result","subtype":"success"}\n')
        stream.feed_eof()

        with patch("orc_core.stream_monitor.asyncio.to_thread", new_callable=AsyncMock) as to_thread_mock:
            to_thread_mock.side_effect = lambda func, *args: func(*args)
            await monitor._read_stdout(stream)

        to_thread_mock.assert_awaited_once()
        monitor._append_agent_output.assert_called_once_with(
            "stdout",
            '{"type":"result","subtype":"success"}\n',
        )
        monitor._record_event.assert_called_once_with({"type": "result", "subtype": "success"})

    async def test_read_stderr_offloads_agent_output_write_to_thread(self) -> None:
        monitor = StreamJsonMonitor.__new__(StreamJsonMonitor)
        monitor._stop = threading.Event()
        monitor._append_agent_output = MagicMock()
        monitor.log_path = Path("/tmp/orc.log")
        monitor.last_output_time = 0.0
        monitor.last_stderr_line = ""
        monitor.stderr_count = 0
        monitor.proc = SimpleNamespace(returncode=None)

        stream = asyncio.StreamReader()
        stream.feed_data(b"warning\n")
        stream.feed_eof()

        with patch("orc_core.stream_monitor.asyncio.to_thread", new_callable=AsyncMock) as to_thread_mock:
            to_thread_mock.side_effect = lambda func, *args: func(*args)
            await monitor._read_stderr(stream)

        to_thread_mock.assert_awaited_once()
        monitor._append_agent_output.assert_called_once_with("stderr", "warning\n")
        self.assertEqual(monitor.last_stderr_line, "warning")
        self.assertEqual(monitor.stderr_count, 1)


if __name__ == "__main__":
    unittest.main()
