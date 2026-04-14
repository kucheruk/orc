#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpers the teamlead uses to read stats and find raw-stream logs."""

from __future__ import annotations

import json
from pathlib import Path

from ..infra.state.state_paths import run_root, stats_path


def find_latest_agent_log(workdir: str, card_id: str) -> str:
    """Find the most recent raw-stream log for a card across all kanban sessions."""
    runs_dir = run_root(workdir, "").parent / "runs"
    if not runs_dir.exists():
        return ""
    best: Path | None = None
    for session_dir in runs_dir.iterdir():
        if not session_dir.name.startswith("kanban-"):
            continue
        stream_dir = session_dir / "raw-stream"
        if not stream_dir.is_dir():
            continue
        for log_file in stream_dir.glob(f"*__{card_id}.log"):
            if best is None or log_file.stat().st_mtime > best.stat().st_mtime:
                best = log_file
    return str(best) if best else ""


def load_token_stats(workdir: str) -> dict[str, int]:
    """Load per-task token stats from analytics."""
    path = stats_path(workdir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("tokens_by_task", {})
        return {k: int(v) for k, v in raw.items() if isinstance(v, (int, float))}
    except Exception:
        return {}
