#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, RichLog


class PostMortemScreen(Screen[None]):
    BINDINGS = [("escape", "exit_app", "Exit")]

    def __init__(
        self,
        *,
        task_id: str,
        exit_code: int,
        failure_reason: str,
        reasoning_lines: list[str],
        recent_events: list[str],
        error_text: str = "",
        debug_log_path: str = "",
        debug_log_name: str = "",
    ) -> None:
        super().__init__()
        self._task_id = task_id
        self._exit_code = int(exit_code)
        self._failure_reason = str(failure_reason or "").strip() or "fatal_error"
        self._reasoning_lines = list(reasoning_lines)
        self._recent_events = list(recent_events)
        self._error_text = str(error_text or "").strip()
        debug_value = str(debug_log_path or "").strip() or str(debug_log_name or "").strip()
        self._debug_log_path = debug_value

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="postmortem_root"):
            yield Label(
                f"[bold white on red]FATAL: {self._failure_reason}[/bold white on red] "
                "[bold]Esc[/bold] — выйти",
                id="postmortem_banner",
            )
            details = f"Task: {self._task_id} | Exit code: {self._exit_code}"
            if self._debug_log_path:
                details = f"{details} | Debug log: {self._debug_log_path}"
            yield Label(details, id="postmortem_details")
            yield Label("Reasoning", classes="section")
            yield RichLog(id="postmortem_reasoning", wrap=True, highlight=True, markup=True)
            yield Label("Event Feed", classes="section")
            yield RichLog(id="postmortem_events", wrap=True, highlight=True, markup=True)
            if self._error_text:
                yield Label("Traceback", classes="section")
                yield RichLog(id="postmortem_traceback", wrap=False, highlight=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._fill_log("postmortem_reasoning", self._reasoning_lines, empty="reasoning is not available")
        self._fill_log("postmortem_events", self._recent_events, empty="events are not available")
        if self._error_text:
            traceback_lines = self._error_text.splitlines() or [self._error_text]
            self._fill_log("postmortem_traceback", traceback_lines[-40:], empty="")

    def _fill_log(self, widget_id: str, lines: list[str], *, empty: str) -> None:
        log = self.query_one(f"#{widget_id}", RichLog)
        log.clear()
        rows = lines if lines else ([empty] if empty else [])
        for row in rows[-20:]:
            log.write(row)

    def action_exit_app(self) -> None:
        self.app.exit(self._exit_code)
