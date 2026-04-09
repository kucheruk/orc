#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main kanban screen: metrics bar + board columns + decision journal + chat input.

Keyboard navigation (vim-like):
  Esc (from input) → enter nav mode   |  i / slash → back to input mode
  Left / Right     → switch column     |  Up / Down → select card
  Enter            → open card detail  |  Esc (nav) → quit
"""

from __future__ import annotations

import time as _time

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog

from ...kanban_constants import STAGES
from ...kanban_snapshot import CardSnapshot, JournalEntry, KanbanBoardSnapshot
from ..kanban_messages import InboxCardRequested, UnblockCardRequested
from .kanban_card_widget import KanbanCardWidget
from .kanban_column import KanbanColumnWidget


class KanbanScreen(Screen[None]):

    BINDINGS = [
        ("t", "app.toggle_dark", "Theme"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._nav_mode: bool = False
        self._sel_col: int = 0
        self._sel_card_id: str | None = None
        self._last_snapshot: KanbanBoardSnapshot | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="kanban_root"):
            yield Label("Metrics: loading...", id="kanban_metrics")
            with Horizontal(id="kanban_board"):
                for stage in STAGES:
                    yield KanbanColumnWidget(stage, id=f"kcol_{stage}")
            with Vertical(id="kanban_journal_area"):
                yield Label("Decision Journal", classes="section")
                yield RichLog(id="kanban_journal", wrap=True, highlight=True, markup=True)
            with Horizontal(id="kanban_input_area"):
                yield Input(placeholder="Add to inbox... | /unblock TASK-ID  [Esc=navigate]", id="kanban_input")
                yield Button("+", id="kanban_add_btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.5, self._tick_spinners)

    # ── Keyboard navigation ────────────────────────────────────

    def on_key(self, event: Key) -> None:
        if not self._nav_mode:
            if event.key == "escape":
                event.stop()
                event.prevent_default()
                self._enter_nav_mode()
            return

        handled = True
        match event.key:
            case "left":
                self._nav_left()
            case "right":
                self._nav_right()
            case "up":
                self._nav_up()
            case "down":
                self._nav_down()
            case "enter":
                self._open_card()
            case "i" | "slash":
                self._exit_nav_mode()
            case "escape":
                self.app.action_request_quit()
            case _:
                handled = False

        if handled:
            event.stop()
            event.prevent_default()

    def _enter_nav_mode(self) -> None:
        self._nav_mode = True
        self.set_focus(None)
        if self._sel_card_id is None:
            self._select_first_card_in_column()
        self._update_selection()

    def _exit_nav_mode(self) -> None:
        self._nav_mode = False
        self._clear_selection_visuals()
        try:
            self.query_one("#kanban_input", Input).focus()
        except Exception:
            pass

    def _nav_left(self) -> None:
        if self._sel_col > 0:
            self._sel_col -= 1
            self._select_first_card_in_column()
            self._update_selection()

    def _nav_right(self) -> None:
        if self._sel_col < len(STAGES) - 1:
            self._sel_col += 1
            self._select_first_card_in_column()
            self._update_selection()

    def _nav_up(self) -> None:
        cards = self._cards_in_current_column()
        if not cards:
            return
        idx = self._find_card_index(cards)
        if idx > 0:
            self._sel_card_id = cards[idx - 1].id
            self._update_selection()

    def _nav_down(self) -> None:
        cards = self._cards_in_current_column()
        if not cards:
            return
        idx = self._find_card_index(cards)
        if idx < len(cards) - 1:
            self._sel_card_id = cards[idx + 1].id
            self._update_selection()

    def _open_card(self) -> None:
        if self._sel_card_id is None:
            return
        card = self._find_card_snapshot(self._sel_card_id)
        if card is None:
            return
        from .card_detail_screen import CardDetailScreen
        self.app.push_screen(CardDetailScreen(card))

    # ── Selection helpers ──────────────────────────────────────

    def _cards_in_current_column(self) -> tuple[CardSnapshot, ...]:
        if self._last_snapshot is None:
            return ()
        stage_name = STAGES[self._sel_col]
        for stage in self._last_snapshot.stages:
            if stage.name == stage_name:
                return stage.cards
        return ()

    def _find_card_index(self, cards: tuple[CardSnapshot, ...] | list[CardSnapshot]) -> int:
        for i, c in enumerate(cards):
            if c.id == self._sel_card_id:
                return i
        return 0

    def _select_first_card_in_column(self) -> None:
        cards = self._cards_in_current_column()
        self._sel_card_id = cards[0].id if cards else None

    def _find_card_snapshot(self, card_id: str) -> CardSnapshot | None:
        if self._last_snapshot is None:
            return None
        for stage in self._last_snapshot.stages:
            for c in stage.cards:
                if c.id == card_id:
                    return c
        return None

    def _update_selection(self) -> None:
        # Column headers
        for i, stage in enumerate(STAGES):
            try:
                hdr = self.query_one(f"#col_hdr_{stage}", Label)
                if i == self._sel_col and self._nav_mode:
                    hdr.add_class("col-selected")
                else:
                    hdr.remove_class("col-selected")
            except Exception:
                pass

        # Card widgets
        for stage in STAGES:
            try:
                col = self.query_one(f"#kcol_{stage}", KanbanColumnWidget)
                body = col.query_one(f"#col_body_{stage}")
                for card_w in body.query(KanbanCardWidget):
                    if card_w.card_id == self._sel_card_id and self._nav_mode:
                        card_w.add_class("card-selected")
                        card_w.scroll_visible()
                    else:
                        card_w.remove_class("card-selected")
            except Exception:
                pass

    def _clear_selection_visuals(self) -> None:
        for stage in STAGES:
            try:
                self.query_one(f"#col_hdr_{stage}", Label).remove_class("col-selected")
            except Exception:
                pass
            try:
                col = self.query_one(f"#kcol_{stage}", KanbanColumnWidget)
                body = col.query_one(f"#col_body_{stage}")
                for card_w in body.query(KanbanCardWidget):
                    card_w.remove_class("card-selected")
            except Exception:
                pass

    def _restore_selection(self) -> None:
        """Re-apply selection after board refresh. Follow card if it moved columns."""
        if not self._nav_mode or self._sel_card_id is None:
            return
        # Check if card is still in current column
        cards = self._cards_in_current_column()
        if any(c.id == self._sel_card_id for c in cards):
            self._update_selection()
            return
        # Card moved — search all columns
        if self._last_snapshot:
            for i, stage in enumerate(self._last_snapshot.stages):
                for c in stage.cards:
                    if c.id == self._sel_card_id:
                        self._sel_col = i
                        self._update_selection()
                        return
        # Card gone — select next in same column
        if cards:
            self._sel_card_id = cards[0].id
        else:
            self._sel_card_id = None
        self._update_selection()

    # ── Board updates ───────────────────────────────────────────

    def update_board(self, snapshot: KanbanBoardSnapshot) -> None:
        self._last_snapshot = snapshot
        self._update_metrics(snapshot)
        for stage_snap in snapshot.stages:
            self._update_column(stage_snap)
        self._restore_selection()

    def _update_metrics(self, snapshot: KanbanBoardSnapshot) -> None:
        m = snapshot.metrics
        parts = [
            f"Lead Time: {m.avg_lead_time_minutes:.1f}m",
            f"Throughput: {m.throughput_per_hour:.1f}/hr",
            f"Cards: {m.total_cards}",
            f"Done: {m.done_cards}",
        ]
        if m.blocked_cards:
            parts.append(f"[red]Blocked: {m.blocked_cards}[/red]")
        try:
            self.query_one("#kanban_metrics", Label).update(" | ".join(parts))
        except Exception:
            pass

    def _update_column(self, stage_snap) -> None:
        try:
            col = self.query_one(f"#kcol_{stage_snap.name}", KanbanColumnWidget)
            col.update_from_snapshot(stage_snap)
        except Exception:
            pass

    # ── Journal ─────────────────────────────────────────────────

    def add_journal_entry(self, entry: JournalEntry) -> None:
        try:
            log = self.query_one("#kanban_journal", RichLog)
            log.write(entry.format_line())
        except Exception:
            pass

    # ── Input ───────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "kanban_input":
            self._submit_inbox(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "kanban_add_btn":
            try:
                inp = self.query_one("#kanban_input", Input)
                self._submit_inbox(inp.value)
            except Exception:
                pass

    def _submit_inbox(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._journal_user("Type a card title or /unblock TASK-ID")
            return
        msg = _parse_command(text)
        if msg is not None:
            self.post_message(msg)
            self._journal_user(f"Command: {text}")
        else:
            self.post_message(InboxCardRequested(text))
            self._journal_user(f"Adding to inbox: {text}")
        try:
            self.query_one("#kanban_input", Input).value = ""
        except Exception:
            pass

    def _journal_user(self, text: str) -> None:
        entry = JournalEntry(timestamp=_time.time(), category="user", card_id="", message=text)
        self.add_journal_entry(entry)

    # ── Spinner animation ───────────────────────────────────────

    def _tick_spinners(self) -> None:
        for stage in STAGES:
            try:
                col = self.query_one(f"#kcol_{stage}", KanbanColumnWidget)
                col.tick_spinners()
            except Exception:
                pass

    # ── Compatibility methods (called by OrcApp for session events) ──

    def add_session(self, session_id: str) -> None:
        pass

    async def remove_session(self, session_id: str) -> None:
        pass

    def update_session(self, session_id: str, snapshot) -> None:
        pass

    def mark_session_failed(self, session_id: str) -> None:
        pass

    def mark_session_closing(self, session_id: str) -> None:
        pass

    def set_task_body(self, session_id: str, body: str) -> None:
        pass

    def set_global_status(self, text: str) -> None:
        pass

    def set_quit_after_task_requested(self, requested: bool) -> None:
        pass


def _parse_command(text: str):
    """Parse /unblock command. Returns a Message or None."""
    parts = text.split(maxsplit=2)
    cmd = parts[0].lower() if parts else ""
    card_id = parts[1].strip() if len(parts) > 1 else ""
    rest = parts[2].strip() if len(parts) > 2 else ""

    if cmd == "/unblock" and card_id:
        return UnblockCardRequested(card_id, rest)
    return None
