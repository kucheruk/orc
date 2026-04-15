#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concrete adapter for tasks.ports.TaskStateWriter — FS-backed implementation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .atomic_io import write_json_atomic, write_text_atomic
from .runtime_state import (
    delete_runtime_state_file,
    init_runtime_payload,
    load_runtime_payload,
    runtime_state_path,
)


class FsTaskStateWriter:
    """Writes task state via atomic file I/O."""

    def write_json(self, path: Path, payload: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
        write_json_atomic(path, payload, ensure_ascii=ensure_ascii, indent=indent)

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        write_text_atomic(path, content, encoding=encoding)

    def delete_runtime_state(self, task_path: Path, log_path: Path, *, reason: str) -> bool:
        return delete_runtime_state_file(task_path, log_path, reason=reason)

    def init_runtime_state(self, task_path: Path, task_id: str) -> Path:
        runtime_path = runtime_state_path(task_path)
        write_json_atomic(runtime_path, init_runtime_payload(task_id), ensure_ascii=False, indent=2)
        return runtime_path

    def read_runtime_payload(self, task_path: Path) -> dict:
        return load_runtime_payload(runtime_state_path(task_path))


DEFAULT_TASK_STATE_WRITER = FsTaskStateWriter()
