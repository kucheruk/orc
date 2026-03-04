#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
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

    def __init__(self) -> None:
        super().__init__()
        self._quit_after_task_requested = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="exec_root"):
            yield Label("", id="task_label")
            yield Label("", id="mode_label")
            yield Label("", id="stats_label")
            yield ProgressBar(total=1, id="progress")
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

    def watch_eta_seconds(self, _value: Optional[float]) -> None:
        self._refresh_stats_and_activity()

    def watch_total_lines(self, _value: int) -> None:
        self._refresh_stats_and_activity()

    def _format_duration(self, seconds: float) -> str:
        mins, secs = divmod(int(max(seconds, 0.0)), 60)
        return f"{mins:02d}:{secs:02d}"

    def _activity_markup(self, idle_seconds: Optional[float]) -> str:
        if idle_seconds is None:
            return "[blue]Agent activity: starting, no messages yet[/blue]"
        if idle_seconds < 15.0:
            return "[green]Agent activity: active now[/green]"
        if idle_seconds < 60.0:
            return f"[yellow]Agent activity: waiting {self._format_duration(idle_seconds)}[/yellow]"
        return f"[red]Agent activity: idle {self._format_duration(idle_seconds)}[/red]"

    def _format_eta(self, eta_seconds: Optional[float]) -> str:
        if eta_seconds is None:
            return "unknown"
        return self._format_duration(eta_seconds)

    def _progress_delta_markup(self) -> str:
        if self.progress_added_delta <= 0:
            return ""
        return f" [yellow](+{self.progress_added_delta})[/yellow]"

    def _refresh_task_label(self) -> None:
        delta = self._progress_delta_markup()
        progress_part = f" | Progress: {self.progress_done}/{self.progress_total}{delta}"
        self.query_one("#task_label", Label).update(f"{self.task_title}{progress_part}")

    def _refresh_mode_label(self) -> None:
        if self._quit_after_task_requested:
            self.query_one("#mode_label", Label).update("[bold red]QUIT AFTER TASK: ACTIVE[/bold red]")
            return
        self.query_one("#mode_label", Label).update("[green]Mode: normal[/green]")

    def _refresh_stats_and_activity(self) -> None:
        elapsed = int(max(time.time() - self.started_at, 0.0))
        self._refresh_mode_label()
        debug_log_path = get_debug_log_path()
        debug_part = f" | Debug log: {debug_log_path}" if debug_log_path is not None else ""
        git_part = f" | Git: [green]+{self.git_added}[/green] [red]-{self.git_deleted}[/red]"
        delta_part = f" [yellow](+{self.progress_added_delta})[/yellow]" if self.progress_added_delta > 0 else ""
        eta_text = self._format_eta(self.eta_seconds)
        self.query_one("#stats_label", Label).update(
            f"Elapsed: {self._format_duration(elapsed)} | "
            f"Done: {self.progress_done} | Ahead: {self.progress_remaining} | "
            f"Total: {self.progress_total}{delta_part} | ETA: {eta_text} | "
            f"Lines: {self.total_lines} | Commands: {self.commands_count} | "
            f"Files: {self.files_edited}{git_part} | Tokens: {self.tokens_total}{debug_part}"
        )
        idle_seconds = None if self.last_event_at is None else max(time.time() - self.last_event_at, 0.0)
        self.query_one("#activity_label", Label).update(self._activity_markup(idle_seconds))

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
