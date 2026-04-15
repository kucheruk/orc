#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concrete adapter for tasks.ports.TaskStateWriter — FS-backed implementation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .atomic_io import write_json_atomic
from .runtime_state import delete_runtime_state_file


class FsTaskStateWriter:
    """Writes task state via atomic file I/O."""

    def write_json(self, path: Path, payload: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
        write_json_atomic(path, payload, ensure_ascii=ensure_ascii, indent=indent)

    def delete_runtime_state(self, task_path: Path, log_path: Path, *, reason: str) -> bool:
        return delete_runtime_state_file(task_path, log_path, reason=reason)


DEFAULT_TASK_STATE_WRITER = FsTaskStateWriter()
