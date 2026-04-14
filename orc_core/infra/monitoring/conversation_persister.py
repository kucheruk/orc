#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persists the agent-side conversation (session) id into task state JSON."""

from __future__ import annotations

import json
from pathlib import Path

from ..io.atomic_io import write_json_atomic
from ..io.logging import log_event


class ConversationIdPersister:
    """Writes conversation_id into the task state file on first observation.

    Reads existing state, refuses to overwrite a non-empty value, and writes
    atomically. All errors are logged but never raised — this is a best-effort
    breadcrumb for resume.
    """

    def __init__(self, task_state_path: Path, task_id: str, log_path: Path) -> None:
        self._task_state_path = task_state_path
        self._task_id = task_id
        self._log_path = log_path

    def persist(self, session_id: str) -> None:
        try:
            if not self._task_state_path.exists():
                return
            payload = json.loads(self._task_state_path.read_text(encoding="utf-8"))
            existing = str(payload.get("conversation_id") or "").strip()
            if existing:
                return
            payload["conversation_id"] = session_id
            write_json_atomic(self._task_state_path, payload, ensure_ascii=False, indent=2)
            log_event(self._log_path, "INFO", "conversation_id captured from stream",
                      session_id=session_id, task_id=self._task_id)
        except Exception as exc:
            log_event(self._log_path, "WARN", "failed to persist conversation_id from stream",
                      error=str(exc), session_id=session_id)
