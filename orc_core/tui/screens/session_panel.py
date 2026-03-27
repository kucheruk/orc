#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single-session display panel with adaptive detail levels."""

import logging
import re
import time
from pathlib import Path

_logger = logging.getLogger(__name__)

from rich.table import Table
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, RichLog, Static

from ...session_types import (
    EVENTS_LINES_FULL,
    EVENTS_LINES_MEDIUM,
    HEADING_MAX_LENGTH,
    HEADING_TRUNCATE_COMPACT,
    HEADING_TRUNCATE_MEDIUM,
    LAST_LINE_COMMAND_TRUNCATE,
    LAST_LINE_FILE_TRUNCATE,
    LAST_LINE_SOLO_TRUNCATE,
    PLACEHOLDER_COMMANDS,
    PLACEHOLDER_FILES,
    PLACEHOLDER_LAST,
    PLACEHOLDER_WAITING,
    RECENT_COMMANDS_COUNT,
    RECENT_FILES_COUNT,
    REASONING_LINES_COMPACT,
    RECENT_LOG_MAX_LINES,
    STALL_THRESHOLD_SECONDS,
    STATUS_TRUNCATE_COMPACT,
    STATUS_TRUNCATE_FULL,
    STATUS_TRUNCATE_MEDIUM,
)
from ...stream_monitor_state import MonitorSnapshot


_STATUS_TRUNCATE = {
    "full": STATUS_TRUNCATE_FULL,
    "medium": STATUS_TRUNCATE_MEDIUM,
}

_HEADING_TRUNCATE = {
    "medium": HEADING_TRUNCATE_MEDIUM,
}


class SessionPanel(Widget):
    DEFAULT_CLASSES = "session-panel"

    detail_level = reactive("full")
    input_bytes = reactive(0)
    output_bytes = reactive(0)
    progress_in_progress = reactive(0)
    files_edited = reactive("-")
    git_added = reactive("-")
    git_deleted = reactive("-")
    commands_count = reactive(0)
    total_lines = reactive(0)
    task_title = reactive("")
    progress_done = reactive(0)
    progress_total = reactive(1)
    progress_remaining = reactive(1)
    progress_added_delta = reactive(0)
    started_at = reactive(0.0)
    live_phase = reactive("starting")
    live_status = reactive("starting, no messages yet")
    live_since = reactive(0.0)
    active_tool_call_count = reactive(0)
    is_subagent_activity = reactive(False)

    def __init__(self, session_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session_id = session_id
        self._quit_after_task = False
        self._heading_cache: dict[str, str] = {}
        self._last_command = ""
        self._last_file = ""
        self._task_body = ""

    def compose(self) -> ComposeResult:
        sid = self.session_id
        yield Label("", id=f"task_label_{sid}", classes="panel-task")
        yield Static("", id=f"task_body_{sid}", classes="panel-task-body")
        yield Label("", id=f"activity_label_{sid}", classes="panel-activity")
        with Vertical(classes="panel-stats-section"):
            yield Label("", id=f"mode_label_{sid}", classes="panel-mode")
            yield Label("", id=f"stats_label_{sid}", classes="panel-stats")
            yield ProgressBar(total=1, id=f"progress_{sid}", classes="panel-progress")
        with Grid(classes="panel-recent"):
            yield Static("", id=f"recent_commands_{sid}")
            yield Static("", id=f"recent_files_{sid}")
        with Vertical(classes="panel-reasoning-section"):
            yield Label("Reasoning", classes="section")
            yield RichLog(id=f"reasoning_log_{sid}", wrap=True, highlight=True,
                          markup=True, classes="panel-reasoning")
        with Vertical(classes="panel-events-section"):
            yield Label("Event Feed", classes="section")
            yield RichLog(id=f"events_log_{sid}", wrap=True, highlight=True,
                          markup=True, classes="panel-events")
        yield Label("", id=f"last_line_{sid}", classes="panel-last-line")

    def on_mount(self) -> None:
        self.add_class("detail-full")

    # ── Reactive watchers ────────────────────────────────────────

    def watch_detail_level(self, old_value: str, new_value: str) -> None:
        if old_value:
            self.remove_class(f"detail-{old_value}")
        self.add_class(f"detail-{new_value}")
        self._refresh_all()

    def watch_task_title(self, _v: str) -> None:
        self._refresh_task_label()

    def watch_progress_done(self, _v: int) -> None:
        self._update_progress_bar()
        self._refresh_task_label()
        self._refresh_stats()

    def watch_progress_total(self, _v: int) -> None:
        self._update_progress_bar()
        self._refresh_task_label()
        self._refresh_stats()

    def watch_progress_remaining(self, _v: int) -> None:
        self._refresh_stats()

    def watch_progress_added_delta(self, _v: int) -> None:
        self._refresh_task_label()
        self._refresh_stats()

    def watch_total_lines(self, _v: int) -> None:
        self._refresh_stats()

    # ── Snapshot update ──────────────────────────────────────────

    def update_from_snapshot(self, snapshot: MonitorSnapshot) -> None:
        self._apply_metrics(snapshot)
        self._apply_live_status(snapshot)
        self._track_recent(snapshot)
        self._update_logs(snapshot)
        self._refresh_stats()

    def _apply_metrics(self, snap: MonitorSnapshot) -> None:
        self.task_title = snap.task_id
        self.started_at = snap.started_at
        self.progress_done = snap.progress_done
        self.progress_total = snap.progress_total
        self.progress_remaining = snap.progress_remaining
        self.progress_in_progress = snap.progress_in_progress
        self.progress_added_delta = snap.progress_added_delta
        self.total_lines = snap.metrics.total_lines
        self.commands_count = snap.metrics.command_count
        self.input_bytes = snap.metrics.input_bytes
        self.output_bytes = snap.metrics.output_bytes
        self.files_edited = str(snap.metrics.files_edited or "-")
        self.git_added = str(snap.metrics.git_added if snap.metrics.git_added is not None else "-")
        self.git_deleted = str(snap.metrics.git_deleted if snap.metrics.git_deleted is not None else "-")

    def _apply_live_status(self, snap: MonitorSnapshot) -> None:
        self.live_phase = snap.live_phase
        self.live_status = snap.live_status
        self.live_since = snap.live_since
        self.active_tool_call_count = snap.active_tool_call_count
        self.is_subagent_activity = snap.is_subagent_activity

    def _track_recent(self, snap: MonitorSnapshot) -> None:
        if snap.recent_commands:
            self._last_command = snap.recent_commands[-1]
        if snap.recent_files:
            self._last_file = snap.recent_files[-1]

    def _update_logs(self, snap: MonitorSnapshot) -> None:
        level = self.detail_level
        if level == "full":
            self._update_recent_tables(snap)
            self._write_log("reasoning_log", snap.reasoning_lines)
            self._write_log("events_log", snap.recent_events[-EVENTS_LINES_FULL:])
        elif level == "medium":
            self._update_recent_tables(snap)
            self._write_log("reasoning_log", snap.reasoning_lines)
            self._write_log("events_log", snap.recent_events[-EVENTS_LINES_MEDIUM:])
        elif level == "compact":
            self._update_recent_tables(snap)
            self._write_log("reasoning_log", snap.reasoning_lines)
            self._write_log("events_log", snap.recent_events[-EVENTS_LINES_MEDIUM:])
        elif level == "minimal":
            self._refresh_last_line()

    # ── Refresh helpers ──────────────────────────────────────────

    def _refresh_task_label(self) -> None:
        self._set_label("task_label", _format_task_label(
            task_id=self.task_title, done=self.progress_done,
            in_progress=self.progress_in_progress,
            total=self.progress_total, delta=self.progress_added_delta,
            heading=self._get_heading(self.task_title), detail=self.detail_level))

    def _refresh_stats(self) -> None:
        elapsed = _format_duration(time.time() - self.started_at) if self.started_at > 0 else "00:00"
        self._set_label("stats_label", _format_stats(
            elapsed=elapsed, detail=self.detail_level,
            done=self.progress_done, remaining=self.progress_remaining,
            total=self.progress_total, delta=self.progress_added_delta,
            lines=self.total_lines, commands=self.commands_count,
            files=self.files_edited, git_added=self.git_added,
            git_deleted=self.git_deleted,
            input_bytes=self.input_bytes, output_bytes=self.output_bytes))
        self._set_label("activity_label", _format_activity(
            phase=self.live_phase, status=self.live_status,
            since=self.live_since, tool_count=self.active_tool_call_count,
            is_subagent=self.is_subagent_activity, detail=self.detail_level))
        if self.detail_level == "full":
            self._refresh_mode_label()

    def _refresh_mode_label(self) -> None:
        text = ("[bold red]QUIT AFTER TASK: ACTIVE[/bold red]"
                if self._quit_after_task else "[green]Mode: normal[/green]")
        self._set_label("mode_label", text)

    def _refresh_last_line(self) -> None:
        cmd = self._last_command or PLACEHOLDER_LAST
        file = self._last_file
        text = (f"Last: {cmd[:LAST_LINE_COMMAND_TRUNCATE]} -> {file[:LAST_LINE_FILE_TRUNCATE]}"
                if file else f"Last: {cmd[:LAST_LINE_SOLO_TRUNCATE]}")
        self._set_label("last_line", text)

    def _refresh_all(self) -> None:
        self._refresh_task_label()
        self._refresh_stats()
        if self.detail_level == "minimal":
            self._refresh_last_line()

    # ── Widget access ────────────────────────────────────────────

    def _wid(self, base: str) -> str:
        return f"{base}_{self.session_id}"

    def _set_label(self, base: str, text: str) -> None:
        try:
            self.query_one(f"#{self._wid(base)}", Label).update(text)
        except NoMatches:
            _logger.debug("label not mounted yet: %s", self._wid(base))

    def _update_progress_bar(self) -> None:
        try:
            bar = self.query_one(f"#{self._wid('progress')}", ProgressBar)
            bar.update(total=max(1, self.progress_total), progress=max(0, self.progress_done))
        except NoMatches:
            _logger.debug("progress bar not mounted yet: %s", self._wid("progress"))

    def _write_log(self, base: str, lines: list[str]) -> None:
        try:
            log = self.query_one(f"#{self._wid(base)}", RichLog)
        except NoMatches:
            _logger.debug("log widget not mounted yet: %s", self._wid(base))
            return
        log.clear()
        for row in (lines or [PLACEHOLDER_WAITING])[-RECENT_LOG_MAX_LINES:]:
            log.write(row)

    def _update_recent_tables(self, snap: MonitorSnapshot) -> None:
        self._set_table("recent_commands", "Recent Commands", "Command",
                        snap.recent_commands[-RECENT_COMMANDS_COUNT:] or [PLACEHOLDER_COMMANDS])
        self._set_table("recent_files", "Recent Files", "Path",
                        snap.recent_files[-RECENT_FILES_COUNT:] or [PLACEHOLDER_FILES])

    def _set_table(self, base: str, title: str, col: str, rows: list[str]) -> None:
        table = Table(title=title, expand=True)
        table.add_column(col)
        for row in rows:
            table.add_row(row)
        try:
            self.query_one(f"#{self._wid(base)}", Static).update(table)
        except NoMatches:
            _logger.debug("table widget not mounted yet: %s", self._wid(base))

    # ── Heading lookup ───────────────────────────────────────────

    def _get_heading(self, task_id: str) -> str:
        if not task_id:
            return ""
        if task_id in self._heading_cache:
            return self._heading_cache[task_id]
        heading = _read_task_heading(task_id)
        self._heading_cache[task_id] = heading
        return heading

    def set_task_body(self, body: str) -> None:
        self._task_body = body
        try:
            widget = self.query_one(f"#{self._wid('task_body')}", Static)
            widget.update(f"[dim]{body}[/dim]")
        except NoMatches:
            _logger.debug("task_body widget not mounted yet: %s", self._wid("task_body"))

    def set_quit_after_task_requested(self, requested: bool) -> None:
        self._quit_after_task = requested
        if self.is_mounted:
            self._refresh_mode_label()


# ── Pure formatting ──────────────────────────────────────────────

def _format_duration(seconds: float) -> str:
    mins, secs = divmod(int(max(seconds, 0.0)), 60)
    return f"{mins:02d}:{secs:02d}"


def _human_bytes(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f}K"
    return f"{n / (1024 * 1024):.1f}M"


def _format_io(input_bytes: int, output_bytes: int) -> str:
    return f"In: {_human_bytes(input_bytes)} | Out: {_human_bytes(output_bytes)}"


def _short_io(input_bytes: int, output_bytes: int) -> str:
    return f"I:{_human_bytes(input_bytes)} O:{_human_bytes(output_bytes)}"


def _format_task_label(*, task_id, done, in_progress, total, delta, heading, detail) -> str:
    delta_str = f" (+{delta})" if delta > 0 else ""
    progress = f"{done}+{in_progress}/{total}" if in_progress > 0 else f"{done}/{total}"
    pct = int(100 * done / max(1, total))
    if detail == "full":
        heading_part = f" | {heading}" if heading else ""
        return f"Task: {task_id} | Progress: {progress}{delta_str}{heading_part}"
    max_len = _HEADING_TRUNCATE.get(detail, HEADING_TRUNCATE_COMPACT)
    short = (heading[:max_len] + "...") if len(heading) > max_len else heading
    return f"{task_id} {progress} {pct}%{f' {short}' if short else ''}"


def _format_stats(*, elapsed, detail, done, remaining, total, delta,
                  lines, commands, files, git_added, git_deleted,
                  input_bytes, output_bytes) -> str:
    io = _format_io(input_bytes, output_bytes)
    if detail == "full":
        delta_part = f" [yellow](+{delta})[/yellow]" if delta > 0 else ""
        git = f" | Git: [green]+{git_added}[/green] [red]-{git_deleted}[/red]"
        return (f"Elapsed: {elapsed} | Done: {done} | Ahead: {remaining} | "
                f"Total: {total}{delta_part} | Lines: {lines} | "
                f"Commands: {commands} | Files: {files}{git} | {io}")
    if detail == "medium":
        return f"{elapsed} | Ln:{lines} Cmd:{commands} F:{files} {_short_io(input_bytes, output_bytes)}"
    return f"{elapsed} | {_short_io(input_bytes, output_bytes)} | Ln: {lines}"


def _format_activity(*, phase, status, since, tool_count, is_subagent, detail) -> str:
    phase = str(phase or "starting").strip().lower()
    max_len = _STATUS_TRUNCATE.get(detail, STATUS_TRUNCATE_COMPACT)
    status = str(status or "waiting for output")[:max_len].replace("[", r"\[")
    age = max(time.time() - float(since or 0.0), 0.0) if since else 0.0
    age_text = _format_duration(age)
    role = "SUBAGENT" if is_subagent else "AGENT"

    if phase == "starting":
        return f"[blue]{role} BOOT {status}[/blue]"
    if phase == "thinking":
        return f"[blue]{role} THINK {status} [{age_text}][/blue]"
    if phase in ("tool_call", "subagent"):
        count = max(int(tool_count or 0), 0)
        suffix = f" x{count}" if count > 1 else ""
        color = "magenta" if is_subagent else "cyan"
        return f"[{color}]{role} EXEC {status}{suffix} [{age_text}][/{color}]"
    if phase == "network_problem":
        return f"[red]{role} NETWORK {status} [{age_text}][/red]"
    if phase == "assistant":
        return f"[green]{role} OUTPUT {status} [{age_text}][/green]"
    if age < STALL_THRESHOLD_SECONDS:
        return f"[yellow]{role} WAIT {status} [{age_text}][/yellow]"
    return f"[red]{role} STALL? {status} [{age_text}][/red]"


def _read_task_heading(task_id: str) -> str:
    task_file = Path("tasks") / f"{task_id}.md"
    if not task_file.exists():
        return ""
    try:
        text = task_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    return _extract_heading_after_id(text, task_id)


def _extract_heading_after_id(text: str, task_id: str) -> str:
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
            return _strip_markdown_prefix(line)[:HEADING_MAX_LENGTH]
    return ""


def _strip_markdown_prefix(line: str) -> str:
    clean = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
    clean = re.sub(r"^\s*>\s*", "", clean)
    clean = re.sub(r"^\s*[-*+]\s+", "", clean)
    clean = re.sub(r"^\s*\d+[.)]\s+", "", clean)
    clean = re.sub(r"^\s*\[[ xX]\]\s*", "", clean)
    return clean.strip()
