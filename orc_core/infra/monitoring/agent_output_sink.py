#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sink that appends the raw agent stdout/stderr stream to a transcript file."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TextIO

from ..io.logging import log_event


class AgentOutputSink:
    """Owns the transcript filehandle for raw agent output lines.

    Creates parent directories on open, writes a start header, flushes on
    every append. ``close()`` is idempotent. When the configured path is
    empty/None, all methods become no-ops.
    """

    def __init__(
        self,
        path: Optional[str],
        *,
        task_id: str,
        log_path: Path,
    ) -> None:
        self._log_path = log_path
        self._task_id = task_id
        self._file: Optional[TextIO] = None
        resolved = (path or "").strip()
        if not resolved:
            return
        p = Path(resolved)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._file = p.open("a", encoding="utf-8")
        self._file.write(f"# stream start task_id={task_id}\n")
        self._file.flush()
        log_event(self._log_path, "INFO", "agent output stream enabled",
                  task_id=task_id, path=str(p))

    def append(self, stream_name: str, payload: str) -> None:
        if self._file is None:
            return
        self._file.write(f"[{stream_name}] {payload}")
        if not payload.endswith("\n"):
            self._file.write("\n")
        self._file.flush()

    def close(self) -> None:
        f = self._file
        if f is None:
            return
        self._file = None
        try:
            f.close()
        except OSError:
            pass
