#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure formatting helpers for the session panel — no Textual dependencies."""

from __future__ import annotations

import re
import time
from pathlib import Path

from ..display_constants import (
    HEADING_MAX_LENGTH,
    HEADING_TRUNCATE_COMPACT,
    HEADING_TRUNCATE_MEDIUM,
    STALL_THRESHOLD_SECONDS,
    STATUS_TRUNCATE_COMPACT,
    STATUS_TRUNCATE_FULL,
    STATUS_TRUNCATE_MEDIUM,
)


_STATUS_TRUNCATE = {
    "full": STATUS_TRUNCATE_FULL,
    "medium": STATUS_TRUNCATE_MEDIUM,
}

_HEADING_TRUNCATE = {
    "medium": HEADING_TRUNCATE_MEDIUM,
}


def format_duration(seconds: float) -> str:
    mins, secs = divmod(int(max(seconds, 0.0)), 60)
    return f"{mins:02d}:{secs:02d}"


def human_bytes(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}K"
    return f"{n / (1024 * 1024):.1f}M"


def format_io(input_bytes: int, output_bytes: int) -> str:
    return f"In: {human_bytes(input_bytes)} | Out: {human_bytes(output_bytes)}"


def short_io(input_bytes: int, output_bytes: int) -> str:
    return f"I:{human_bytes(input_bytes)} O:{human_bytes(output_bytes)}"


def format_task_label(*, task_id, done, in_progress, total, delta, heading, detail) -> str:
    delta_str = f" (+{delta})" if delta > 0 else ""
    progress = f"{done}+{in_progress}/{total}" if in_progress > 0 else f"{done}/{total}"
    pct = int(100 * done / max(1, total))
    safe_id = str(task_id).replace("[", r"\[")
    if detail == "full":
        heading_part = f" | {heading}" if heading else ""
        return f"Task: {safe_id} | Progress: {progress}{delta_str}{heading_part}"
    max_len = _HEADING_TRUNCATE.get(detail, HEADING_TRUNCATE_COMPACT)
    short = (heading[:max_len] + "...") if len(heading) > max_len else heading
    return f"{safe_id} {progress} {pct}%{f' {short}' if short else ''}"


def format_stats(*, elapsed, detail, done, remaining, total, delta,
                 lines, commands, files, git_added, git_deleted,
                 input_bytes, output_bytes) -> str:
    io = format_io(input_bytes, output_bytes)
    if detail == "full":
        delta_part = f" [yellow](+{delta})[/yellow]" if delta > 0 else ""
        git = f" | Git: [green]+{git_added}[/green] [red]-{git_deleted}[/red]"
        return (f"Elapsed: {elapsed} | Done: {done} | Ahead: {remaining} | "
                f"Total: {total}{delta_part} | Lines: {lines} | "
                f"Commands: {commands} | Files: {files}{git} | {io}")
    if detail == "medium":
        return f"{elapsed} | Ln:{lines} Cmd:{commands} F:{files} {short_io(input_bytes, output_bytes)}"
    return f"{elapsed} | {short_io(input_bytes, output_bytes)} | Ln: {lines}"


_PHASE_FORMATS: dict[str, tuple[str, str]] = {
    "failed":          ("bold red", "FAILED"),
    "completed":       ("bold green", "DONE"),
    "starting":        ("blue", "BOOT"),
    "thinking":        ("blue", "THINK"),
    "network_problem": ("red", "NETWORK"),
    "assistant":       ("green", "OUTPUT"),
}


def format_activity(*, phase, status, since, tool_count, is_subagent, detail) -> str:
    phase = str(phase or "starting").strip().lower()
    max_len = _STATUS_TRUNCATE.get(detail, STATUS_TRUNCATE_COMPACT)
    status = str(status or "waiting for output")[:max_len].replace("[", r"\[")
    age = max(time.time() - float(since or 0.0), 0.0) if since else 0.0
    age_text = format_duration(age)
    role = "SUBAGENT" if is_subagent else "AGENT"

    if phase in ("tool_call", "subagent"):
        count = max(int(tool_count or 0), 0)
        suffix = f" x{count}" if count > 1 else ""
        color = "magenta" if is_subagent else "cyan"
        return f"[{color}]{role} EXEC {status}{suffix} [{age_text}][/{color}]"

    fmt = _PHASE_FORMATS.get(phase)
    if fmt:
        color, label = fmt
        timed = f" [{age_text}]" if phase not in ("failed", "completed", "starting") else ""
        return f"[{color}]{role} {label} {status}{timed}[/{color}]"

    if age < STALL_THRESHOLD_SECONDS:
        return f"[yellow]{role} WAIT {status} [{age_text}][/yellow]"
    return f"[red]{role} STALL? {status} [{age_text}][/red]"


def read_task_heading(task_id: str) -> str:
    task_file = Path("tasks") / f"{task_id}.md"
    if not task_file.exists():
        return ""
    try:
        text = task_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    return extract_heading_after_id(text, task_id)


def extract_heading_after_id(text: str, task_id: str) -> str:
    wanted = task_id.casefold()
    seen = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not seen and wanted in line.casefold():
            seen = True
            continue
        if seen:
            return strip_markdown_prefix(line)[:HEADING_MAX_LENGTH]
    return ""


def strip_markdown_prefix(line: str) -> str:
    clean = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
    clean = re.sub(r"^\s*>\s*", "", clean)
    clean = re.sub(r"^\s*[-*+]\s+", "", clean)
    clean = re.sub(r"^\s*\d+[.)]\s+", "", clean)
    clean = re.sub(r"^\s*\[[ xX]\]\s*", "", clean)
    return clean.strip()
