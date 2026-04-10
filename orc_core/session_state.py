#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Optional

from .atomic_io import write_json_atomic
from .state_paths import (
    active_session_path,
    ensure_parent,
    session_path,
    worktree_record_path,
)


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_active_session(workdir: str, payload: dict) -> Path:
    path = active_session_path(workdir)
    ensure_parent(path)
    write_json_atomic(path, payload, ensure_ascii=False, indent=2)
    return path


def load_active_session(workdir: str) -> dict:
    return load_json(active_session_path(workdir))


def clear_active_session(workdir: str) -> None:
    path = active_session_path(workdir)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def save_session_manifest(workdir: str, session_id: str, payload: dict) -> Path:
    path = session_path(workdir, session_id)
    ensure_parent(path)
    write_json_atomic(path, payload, ensure_ascii=False, indent=2)
    return path


def save_worktree_record(workdir: str, session_id: str, payload: dict) -> Path:
    path = worktree_record_path(workdir, session_id)
    ensure_parent(path)
    write_json_atomic(path, payload, ensure_ascii=False, indent=2)
    return path



