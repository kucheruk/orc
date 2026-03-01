#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from textual.message import Message

from ..stream_monitor_state import MonitorSnapshot


class SnapshotUpdated(Message):
    def __init__(self, snapshot: MonitorSnapshot) -> None:
        self.snapshot = snapshot
        super().__init__()


class OrchestratorFinished(Message):
    def __init__(self, exit_code: int, error_text: str | None = None) -> None:
        self.exit_code = int(exit_code)
        self.error_text = error_text
        super().__init__()
