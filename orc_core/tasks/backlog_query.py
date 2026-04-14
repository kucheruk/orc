#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backlog-query adapter — reads task-runtime payloads and queries the backlog source."""

from __future__ import annotations

import json
from pathlib import Path

from .task_source import MarkdownTaskSource


class MarkdownBacklogQuery:
    """BacklogQueryPort implementation backed by markdown task sources.

    Reads the task-runtime payload at ``task_path``, extracts the backlog
    reference, and asks ``MarkdownTaskSource`` whether the task is done.
    """

    def is_task_done(self, task_path: Path) -> bool:
        try:
            payload = json.loads(task_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return False
        backlog_raw = str(payload.get("backlog_path") or "").strip()
        task_id = str(payload.get("task_id") or "").strip()
        if not backlog_raw or not task_id:
            return False
        try:
            return MarkdownTaskSource(Path(backlog_raw)).is_task_done(task_id)
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            return False
