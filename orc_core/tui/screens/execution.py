#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
from pathlib import Path
from typing import Optional

from rich.table import Table
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ProgressBar, RichLog, Static

from ...logging import get_debug_log_path
from ...stream_monitor_state import MonitorSnapshot


class ExecutionScreen(Screen[None]):
    tokens_total = reactive("-")
    files_edited = reactive("-")
    git_added = reactive("-")
    git_deleted = reactive("-")
    commands_count = reactive(0)
    total_lines = reactive(0)
    task_title = reactive("")
    last_event = reactive("")
    progress_done = reactive(0)
    progress_total = reactive(1)
    progress_remaining = reactive(1)
    progress_added_delta = reactive(0)
    eta_seconds = reactive(None)
    started_at = reactive(0.0)
    last_event_at = reactive(None)
    live_phase = reactive("starting")
    live_status = reactive("starting, no messages yet")
    live_since = reactive(0.0)
    active_tool_call_count = reactive(0)
    is_subagent_activity = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self._quit_after_task_requested = False
        self._task_heading_cache: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="exec_root"):
            yield Label("", id="task_label")
            yield Label("", id="mode_label")
            yield Label("", id="stats_label")
            yield ProgressBar(total=1, id="progress")
            yield Label("", id="debug_log_label")
            yield Label("", id="activity_label")
            with Grid(id="recent_grid"):
                yield Static("", id="recent_commands")
                yield Static("", id="recent_files")
            yield Label("Reasoning", classes="section")
            yield RichLog(id="reasoning_log", wrap=True, highlight=True, markup=True)
            yield Label("Event Feed", classes="section")
            yield RichLog(id="events_log", wrap=True, highlight=True, markup=True)
        yield Footer()

    def watch_task_title(self, value: str) -> None:
        _ = value
        self._refresh_task_label()

    def watch_progress_done(self, value: int) -> None:
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=max(1, self.progress_total), progress=max(0, value))
        self._refresh_task_label()
        self._refresh_stats_and_activity()

    def watch_progress_total(self, value: int) -> None:
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=max(1, value), progress=max(0, self.progress_done))
        self._refresh_task_label()
        self._refresh_stats_and_activity()

    def watch_progress_remaining(self, _value: int) -> None:
        self._refresh_stats_and_activity()

    def watch_progress_added_delta(self, _value: int) -> None:
        self._refresh_task_label()
        self._refresh_stats_and_activity()

    def watch_total_lines(self, _value: int) -> None:
        self._refresh_stats_and_activity()

    def _format_duration(self, seconds: float) -> str:
        mins, secs = divmod(int(max(seconds, 0.0)), 60)
        return f"{mins:02d}:{secs:02d}"

    def _activity_markup(self) -> str:
        phase = str(self.live_phase or "starting").strip().lower()
        status = str(self.live_status or "").strip() or "waiting for output"
        status = status[:96]
        since = float(self.live_since or 0.0)
        age_seconds = max(time.time() - since, 0.0) if since > 0 else 0.0
        age_text = self._format_duration(age_seconds)
        role = "SUBAGENT" if self.is_subagent_activity else "AGENT"

        if phase == "starting":
            return f"[blue]{role} BOOT {status}[/blue]"
        if phase == "thinking":
            return f"[blue]{role} THINK {status} [{age_text}][/blue]"
        if phase in {"tool_call", "subagent"}:
            count = max(int(self.active_tool_call_count or 0), 0)
            tool_suffix = f" x{count}" if count > 1 else ""
            color = "magenta" if (self.is_subagent_activity or phase == "subagent") else "cyan"
            return f"[{color}]{role} EXEC {status}{tool_suffix} [{age_text}][/{color}]"
        if phase == "assistant":
            return f"[green]{role} OUTPUT {status} [{age_text}][/green]"
        if age_seconds < 60.0:
            return f"[yellow]{role} WAIT {status} [{age_text}][/yellow]"
        return f"[red]{role} STALL? {status} [{age_text}][/red]"

    def _format_debug_log_label(self) -> str:
        debug_log_path = get_debug_log_path()
        if debug_log_path is None:
            return ""
        return f"Debug log: {debug_log_path.name}"

    def _progress_delta_markup(self) -> str:
        if self.progress_added_delta <= 0:
            return ""
        return f" [yellow](+{self.progress_added_delta})[/yellow]"

    def _refresh_task_label(self) -> None:
        delta = self._progress_delta_markup()
        progress_part = f" | Progress: {self.progress_done}/{self.progress_total}{delta}"
        heading_part = ""
        task_id = self._extract_task_id_from_label(self.task_title)
        if task_id:
            heading = self._task_heading_for_id(task_id)
            if heading:
                heading_part = f" | {heading}"
        self.query_one("#task_label", Label).update(f"{self.task_title}{progress_part}{heading_part}")

    def _extract_task_id_from_label(self, value: str) -> str:
        prefix = "Task:"
        if not value.startswith(prefix):
            return ""
        return value[len(prefix) :].strip()

    def _task_heading_for_id(self, task_id: str) -> str:
        if not task_id:
            return ""
        if task_id in self._task_heading_cache:
            return self._task_heading_cache[task_id]
        heading = self._read_markdown_heading_after_task_id(task_id)
        self._task_heading_cache[task_id] = heading
        return heading

    def _read_markdown_heading_after_task_id(self, task_id: str) -> str:
        task_file = Path("tasks") / f"{task_id}.md"
        if not task_file.exists():
            return ""
        try:
            lines = task_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        seen_task_id = False
        wanted = task_id.casefold()
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if not seen_task_id and wanted in line.casefold():
                seen_task_id = True
                continue
            if seen_task_id:
                return self._strip_markdown_prefix(line)[:120]
        return ""

    def _strip_markdown_prefix(self, line: str) -> str:
        compact = line.strip()
        compact = re.sub(r"^\s{0,3}#{1,6}\s*", "", compact)
        compact = re.sub(r"^\s*>\s*", "", compact)
        compact = re.sub(r"^\s*[-*+]\s+", "", compact)
        compact = re.sub(r"^\s*\d+[.)]\s+", "", compact)
        compact = re.sub(r"^\s*\[[ xX]\]\s*", "", compact)
        return compact.strip()

    def _refresh_mode_label(self) -> None:
        if self._quit_after_task_requested:
            self.query_one("#mode_label", Label).update(
                "[bold red]QUIT AFTER TASK: ACTIVE (commit phase will run)[/bold red]"
            )
            return
        self.query_one("#mode_label", Label).update("[green]Mode: normal[/green]")

    def _refresh_stats_and_activity(self) -> None:
        elapsed = int(max(time.time() - self.started_at, 0.0))
        self._refresh_mode_label()
        git_part = f" | Git: [green]+{self.git_added}[/green] [red]-{self.git_deleted}[/red]"
        delta_part = f" [yellow](+{self.progress_added_delta})[/yellow]" if self.progress_added_delta > 0 else ""
        self.query_one("#stats_label", Label).update(
            f"Elapsed: {self._format_duration(elapsed)} | "
            f"Done: {self.progress_done} | Ahead: {self.progress_remaining} | "
            f"Total: {self.progress_total}{delta_part} | "
            f"Lines: {self.total_lines} | Commands: {self.commands_count} | "
            f"Files: {self.files_edited}{git_part} | Tokens: {self.tokens_total}"
        )
        self.query_one("#debug_log_label", Label).update(self._format_debug_log_label())
        self.query_one("#activity_label", Label).update(self._activity_markup())

    def update_from_snapshot(self, snapshot: MonitorSnapshot) -> None:
        self.task_title = f"Task: {snapshot.task_id}"
        self.started_at = snapshot.started_at
        self.progress_done = snapshot.progress_done
        self.progress_total = snapshot.progress_total
        self.progress_remaining = snapshot.progress_remaining
        self.progress_added_delta = snapshot.progress_added_delta
        self.eta_seconds = snapshot.eta_seconds
        self.total_lines = snapshot.metrics.total_lines
        self.commands_count = snapshot.metrics.command_count
        if snapshot.metrics.tokens_total is None:
            self.tokens_total = "unknown"
        else:
            token_value = str(snapshot.metrics.tokens_total)
            self.tokens_total = f"~{token_value}" if snapshot.metrics.tokens_status == "estimated" else token_value
        self.files_edited = str(snapshot.metrics.files_edited or "-")
        self.git_added = str(snapshot.metrics.git_added if snapshot.metrics.git_added is not None else "-")
        self.git_deleted = str(snapshot.metrics.git_deleted if snapshot.metrics.git_deleted is not None else "-")
        self.last_event = f"{snapshot.last_event_type}:{snapshot.last_event_note[:80]}"
        self.last_event_at = snapshot.last_event_at if snapshot.last_event_at > 0 else None
        self.live_phase = snapshot.live_phase
        self.live_status = snapshot.live_status
        self.live_since = snapshot.live_since
        self.active_tool_call_count = snapshot.active_tool_call_count
        self.is_subagent_activity = snapshot.is_subagent_activity
        self._update_recent(snapshot)
        self._replace_log("reasoning_log", snapshot.reasoning_lines, empty="waiting for reasoning...")
        self._replace_log("events_log", snapshot.recent_events[-8:], empty="waiting for events...")
        self._refresh_stats_and_activity()

    def _update_recent(self, snapshot: MonitorSnapshot) -> None:
        commands = snapshot.recent_commands[-6:] or ["waiting for tool calls..."]
        files = snapshot.recent_files[-6:] or ["waiting for file operations..."]
        table = Table(title="Recent Commands", expand=True)
        table.add_column("Command")
        for command in commands:
            table.add_row(command)
        self.query_one("#recent_commands", Static).update(table)

        table2 = Table(title="Recent Files", expand=True)
        table2.add_column("Path")
        for file_path in files:
            table2.add_row(file_path)
        self.query_one("#recent_files", Static).update(table2)

    def _replace_log(self, widget_id: str, lines: list[str], *, empty: str) -> None:
        log = self.query_one(f"#{widget_id}", RichLog)
        log.clear()
        rows = lines if lines else [empty]
        for row in rows[-10:]:
            log.write(row)

    def set_quit_after_task_requested(self, requested: bool) -> None:
        self._quit_after_task_requested = requested
        if self.is_mounted:
            self._refresh_stats_and_activity()
