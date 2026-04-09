#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single kanban card widget with spinner, metrics, and color coding."""

from __future__ import annotations

import logging
import re

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label

from ...kanban_snapshot import CardSnapshot

_SPINNER = "⣾⣽⣻⢿⡿⣟⣯⣷"
_logger = logging.getLogger(__name__)


def _css_safe_id(raw: str) -> str:
    """Sanitize a string for use as a CSS-valid widget ID."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", raw)


class KanbanCardWidget(Widget):
    DEFAULT_CLASSES = "kanban-card"

    card_id: str = ""
    _safe_id: str = ""
    is_active = reactive(False)
    spinner_frame = reactive(0)

    def __init__(self, card: CardSnapshot, **kwargs) -> None:
        super().__init__(**kwargs)
        self.card_id = card.id
        self._safe_id = _css_safe_id(card.id)
        self._card = card
        self._apply_classes(card)

    def compose(self) -> ComposeResult:
        cid = self.card_id.replace("[", r"\[")
        yield Label(cid, id=f"kc_head_{self._safe_id}")
        yield Label("", id=f"kc_role_{self._safe_id}")
        yield Label("", id=f"kc_metrics_{self._safe_id}")

    def on_mount(self) -> None:
        self._refresh_labels()

    def update_card(self, card: CardSnapshot) -> None:
        self._card = card
        self._apply_classes(card)
        self.is_active = bool(card.assigned_agent)
        self._refresh_labels()

    def tick_spinner(self) -> None:
        if self.is_active:
            self.spinner_frame = (self.spinner_frame + 1) % len(_SPINNER)
            self._refresh_labels()

    def _apply_classes(self, card: CardSnapshot) -> None:
        for cls in ("card-active", "card-idle", "card-expedite", "card-blocked"):
            self.remove_class(cls)
        if card.action == "Blocked":
            self.add_class("card-blocked")
        elif card.class_of_service == "expedite":
            self.add_class("card-expedite")
        elif card.assigned_agent:
            self.add_class("card-active")
        else:
            self.add_class("card-idle")

    def _refresh_labels(self) -> None:
        c = self._card
        sid = self._safe_id
        safe_id = c.id.replace("[", r"\[")
        title = c.title[:18] if c.title else ""
        if title:
            safe_title = title.replace("[", r"\[")
            head = f"{safe_id} {safe_title}"
        else:
            head = safe_id
        self._set(f"kc_head_{sid}", head)

        if c.assigned_agent:
            spin = _SPINNER[self.spinner_frame % len(_SPINNER)]
            elapsed = _fmt_elapsed(c.elapsed_seconds)
            role_text = f"{spin} {c.action} ({c.assigned_agent}) {elapsed}"
        else:
            role_text = f"[dim]{c.action}[/dim]"
        self._set(f"kc_role_{sid}", role_text)

        io = f"I:{_human(c.input_bytes)} O:{_human(c.output_bytes)}" if c.input_bytes or c.output_bytes else ""
        roi_text = f"ROI:{c.roi}" if c.roi > 0 else ""
        parts = [p for p in (io, roi_text) if p]
        self._set(f"kc_metrics_{sid}", " ".join(parts) if parts else "")

    def _set(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Label).update(text)
        except Exception:
            _logger.debug("Widget #%s not found in card %s", widget_id, self.card_id)


def _fmt_elapsed(seconds: float) -> str:
    if seconds <= 0:
        return ""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _human(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f}K"
    return f"{n / (1024 * 1024):.1f}M"
