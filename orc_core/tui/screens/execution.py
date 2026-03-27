#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grid container for parallel session panels with adaptive layout."""

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer, Header, Label

from ...session_types import DETAIL_LEVEL_DEFAULT, DETAIL_LEVELS, MAX_SESSIONS
from ...stream_monitor_state import MonitorSnapshot
from .session_panel import SessionPanel


_HINT_AVAILABLE = "[+] add | [-] remove"
_HINT_MAX_REACHED = "[-] remove (max reached)"


class ExecutionScreen(Screen[None]):

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="exec_root"):
            yield Label(self._status_text(0), id="global_status")
            yield Grid(id="sessions_grid")
        yield Footer()

    # ── Session management ───────────────────────────────────────

    def add_session(self, session_id: str) -> None:
        grid = self.query_one("#sessions_grid", Grid)
        panel = SessionPanel(session_id=session_id, id=f"panel_{session_id}")
        grid.mount(panel)
        self._recalc_layout()

    def remove_session(self, session_id: str) -> None:
        panel = self._find_panel(session_id)
        if panel:
            panel.remove()
            self._recalc_layout()

    def update_session(self, session_id: str, snapshot: MonitorSnapshot) -> None:
        panel = self._find_panel(session_id)
        if panel:
            panel.update_from_snapshot(snapshot)

    def mark_session_failed(self, session_id: str) -> None:
        panel = self._find_panel(session_id)
        if panel:
            panel.add_class("panel-failed")

    def mark_session_closing(self, session_id: str) -> None:
        panel = self._find_panel(session_id)
        if panel:
            panel.add_class("panel-closing")

    def set_task_body(self, session_id: str, body: str) -> None:
        panel = self._find_panel(session_id)
        if panel:
            panel.set_task_body(body)

    def set_global_status(self, text: str) -> None:
        self.query_one("#global_status", Label).update(text)

    def set_quit_after_task_requested(self, requested: bool) -> None:
        for panel in self.query(SessionPanel):
            panel.set_quit_after_task_requested(requested)

    # ── Layout ───────────────────────────────────────────────────

    def _recalc_layout(self) -> None:
        panels = list(self.query(SessionPanel))
        count = len(panels)
        grid = self.query_one("#sessions_grid", Grid)

        for i in range(1, MAX_SESSIONS + 1):
            grid.remove_class(f"cols-{i}")
        grid.add_class(f"cols-{min(max(count, 1), MAX_SESSIONS)}")

        detail = DETAIL_LEVELS.get(count, DETAIL_LEVEL_DEFAULT)
        for panel in panels:
            panel.detail_level = detail

        self.query_one("#global_status", Label).update(self._status_text(count))

    def _find_panel(self, session_id: str):
        try:
            return self.query_one(f"#panel_{session_id}", SessionPanel)
        except NoMatches:
            return None

    @staticmethod
    def _status_text(count: int) -> str:
        hint = _HINT_AVAILABLE if count < MAX_SESSIONS else _HINT_MAX_REACHED
        return f"Sessions: {count}/{MAX_SESSIONS} | {hint}"
