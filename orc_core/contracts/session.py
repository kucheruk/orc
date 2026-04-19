#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session and monitoring DTOs — shared between tasks/, agents/, board/, tui/, cli/."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MetricsStore:
    tokens_total: Optional[int] = None
    tokens_status: str = "unknown"
    tokens_source: str = "none"
    files_edited: Optional[int] = None
    command_count: int = 0
    total_lines: int = 0
    total_output_chars: int = 0
    input_bytes: int = 0
    output_bytes: int = 0
    git_added: Optional[int] = None
    git_deleted: Optional[int] = None


@dataclass(frozen=True)
class MonitorSnapshot:
    task_id: str
    started_at: float
    progress_done: int
    progress_total: int
    metrics: MetricsStore
    last_event_type: str
    last_event_note: str
    recent_commands: list[str]
    recent_files: list[str]
    recent_events: list[str]
    reasoning_lines: list[str]
    spinner_idx: int
    last_event_at: float
    progress_remaining: int = 0
    progress_in_progress: int = 0
    progress_added_delta: int = 0
    eta_seconds: Optional[float] = None
    live_phase: str = "starting"
    live_status: str = "starting, no messages yet"
    live_since: float = 0.0
    active_tool_call_count: int = 0
    is_subagent_activity: bool = False
