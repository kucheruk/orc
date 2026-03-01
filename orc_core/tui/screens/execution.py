#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

from rich.table import Table
from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ProgressBar, RichLog, Static

from ...stream_monitor_state import MonitorSnapshot


class ExecutionScreen(Screen[None]):
    tokens_total = reactive("-")
    files_edited = reactive("-")
    commands_count = reactive(0)
    total_lines = reactive(0)
    task_title = reactive("")
    last_event = reactive("")
    progress_done = reactive(0)
    progress_total = reactive(1)
    started_at = reactive(0.0)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="exec_root"):
            yield Label("", id="task_label")
            yield Label("", id="stats_label")
            yield ProgressBar(total=1, id="progress")
            with Grid(id="recent_grid"):
                yield Static("", id="recent_commands")
                yield Static("", id="recent_files")
            yield Label("Reasoning", classes="section")
            yield RichLog(id="reasoning_log", wrap=True, highlight=True, markup=True)
            yield Label("Event Feed", classes="section")
            yield RichLog(id="events_log", wrap=True, highlight=True, markup=True)
        yield Footer()

    def watch_task_title(self, value: str) -> None:
        self.query_one("#task_label", Label).update(value)

    def watch_progress_done(self, value: int) -> None:
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=max(1, self.progress_total), progress=max(0, value))

    def watch_progress_total(self, value: int) -> None:
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=max(1, value), progress=max(0, self.progress_done))

    def watch_total_lines(self, _value: int) -> None:
        elapsed = int(max(time.time() - self.started_at, 0.0))
        mins, secs = divmod(elapsed, 60)
        self.query_one("#stats_label", Label).update(
            f"Elapsed: {mins:02d}:{secs:02d} | "
            f"Lines: {self.total_lines} | Commands: {self.commands_count} | "
            f"Files: {self.files_edited} | Tokens: {self.tokens_total} | Last: {self.last_event}"
        )

    def update_from_snapshot(self, snapshot: MonitorSnapshot) -> None:
        self.task_title = f"Task: {snapshot.task_id}"
        self.started_at = snapshot.started_at
        self.progress_done = snapshot.progress_done
        self.progress_total = snapshot.progress_total
        self.total_lines = snapshot.metrics.total_lines
        self.commands_count = snapshot.metrics.command_count
        self.tokens_total = str(snapshot.metrics.tokens_total or "-")
        self.files_edited = str(snapshot.metrics.files_edited or "-")
        self.last_event = f"{snapshot.last_event_type}:{snapshot.last_event_note[:80]}"
        self._update_recent(snapshot)
        self._replace_log("reasoning_log", snapshot.reasoning_lines, empty="waiting for reasoning...")
        self._replace_log("events_log", snapshot.recent_events[-8:], empty="waiting for events...")

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
