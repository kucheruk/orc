#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban column widget: header with WIP status + card list with reconciliation."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Label

from ...kanban_constants import STAGE_ABBREV_NAMES, WIP_STAGES
from ...kanban_snapshot import StageSnapshot
from .kanban_card_widget import KanbanCardWidget

_SHORT_NAMES = STAGE_ABBREV_NAMES


class _NoFocusScroll(VerticalScroll):
    """VerticalScroll that cannot receive focus — prevents arrow key interception."""

    can_focus = False


class KanbanColumnWidget(Widget):
    DEFAULT_CLASSES = "kanban-column"

    def __init__(self, stage_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.stage_name = stage_name
        self._short = _SHORT_NAMES.get(stage_name, stage_name)

    def compose(self) -> ComposeResult:
        yield Label(self._short, id=f"col_hdr_{self.stage_name}", classes="kanban-column-header")
        yield _NoFocusScroll(id=f"col_body_{self.stage_name}", classes="kanban-column-body")

    def update_from_snapshot(self, stage: StageSnapshot) -> None:
        self._update_header(stage)
        self._reconcile_cards(stage)

    def tick_spinners(self) -> None:
        try:
            body = self.query_one(f"#col_body_{self.stage_name}", _NoFocusScroll)
            for card_w in body.query(KanbanCardWidget):
                card_w.tick_spinner()
        except Exception:
            pass

    def _update_header(self, stage: StageSnapshot) -> None:
        has_wip = self.stage_name in WIP_STAGES
        if has_wip and stage.wip_limit < 999:
            text = f"{self._short} ({stage.count}/{stage.wip_limit})"
            free = stage.wip_limit - stage.count
            if free <= 0:
                color_cls = "wip-full"
            elif free == 1:
                color_cls = "wip-warn"
            else:
                color_cls = "wip-ok"
        else:
            text = f"{self._short} ({stage.count})"
            color_cls = "wip-ok"

        try:
            hdr = self.query_one(f"#col_hdr_{self.stage_name}", Label)
            hdr.update(text)
            for cls in ("wip-ok", "wip-warn", "wip-full"):
                hdr.remove_class(cls)
            hdr.add_class(color_cls)
        except Exception:
            pass

    def _reconcile_cards(self, stage: StageSnapshot) -> None:
        try:
            body = self.query_one(f"#col_body_{self.stage_name}", _NoFocusScroll)
        except Exception:
            return

        existing: dict[str, KanbanCardWidget] = {}
        for w in body.query(KanbanCardWidget):
            existing[w.card_id] = w

        new_ids = {c.id for c in stage.cards}

        # Remove cards no longer in this stage
        for cid, w in list(existing.items()):
            if cid not in new_ids:
                w.remove()
                del existing[cid]

        # Add or update cards
        for card_snap in stage.cards:
            if card_snap.id in existing:
                existing[card_snap.id].update_card(card_snap)
            else:
                widget = KanbanCardWidget(card_snap, id=f"kcard_{card_snap.id}")
                body.mount(widget)
