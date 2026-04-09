#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full-screen detail view for a kanban card: live SessionPanel or static info."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label

from ...kanban_snapshot import CardSnapshot
from ...stream_monitor_state import MonitorSnapshot
from .session_panel import SessionPanel


class CardDetailScreen(Screen[None]):

    BINDINGS = [("escape", "dismiss_screen", "Back to Board")]

    def __init__(self, card: CardSnapshot) -> None:
        super().__init__()
        self._card = card
        self._session_panel: SessionPanel | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        if self._card.assigned_agent:
            panel = SessionPanel(self._card.assigned_agent)
            panel.detail_level = "full"
            self._session_panel = panel
            yield panel
        else:
            with Vertical(id="card_info"):
                c = self._card
                yield Label(f"[bold]{c.id}[/bold]  {c.title}", markup=True)
                yield Label(f"Stage: {c.stage}  |  Action: {c.action}")
                yield Label(f"Class of Service: {c.class_of_service}")
                yield Label(f"Value: {c.value_score}  |  Effort: {c.effort_score}  |  ROI: {c.roi:.2f}")
                yield Label(f"Loop count: {c.loop_count}")
                if c.created_at:
                    yield Label(f"Created: {c.created_at}")
                if c.updated_at:
                    yield Label(f"Updated: {c.updated_at}")
                yield Label("")
                yield Label("[dim]No agent assigned. Press Esc to go back.[/dim]", markup=True)
        yield Footer()

    def action_dismiss_screen(self) -> None:
        self.dismiss()

    @property
    def detail_session_id(self) -> str:
        return self._card.assigned_agent or ""

    def update_session(self, session_id: str, snapshot: MonitorSnapshot) -> None:
        if self._session_panel and session_id == self._card.assigned_agent:
            self._session_panel.update_from_snapshot(snapshot)
