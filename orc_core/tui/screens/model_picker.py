#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, RadioButton, RadioSet


class ModelPickerModal(ModalScreen[Optional[str]]):
    BINDINGS = [
        ("enter", "submit", "Select"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, models: list[str], selected_model: str) -> None:
        super().__init__()
        self._models = models
        self._selected_model = selected_model if selected_model in models else models[0]

    def compose(self) -> ComposeResult:
        with Vertical(id="model_picker_modal"):
            yield Label("Выбор модели")
            with RadioSet(id="model_picker_set"):
                for idx, model in enumerate(self._models):
                    yield RadioButton(model, value=model == self._selected_model, id=f"model_pick_{idx}")
            yield Label("Enter — выбрать, Esc — отмена")

    def _selected(self) -> str:
        selected = self.query_one("#model_picker_set", RadioSet).pressed_index
        if selected is None:
            return self._selected_model
        return self._models[selected]

    def action_submit(self) -> None:
        self.dismiss(self._selected())

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(RadioSet.Changed, "#model_picker_set")
    def _on_model_changed(self) -> None:
        # Keep keyboard confirmation explicit via Enter.
        return
