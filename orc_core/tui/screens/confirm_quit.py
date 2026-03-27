#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmQuitModal(ModalScreen[bool]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Yes"),
        ("enter", "confirm", "Confirm"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit_modal"):
            yield Label("Остановить ORC и выйти? (y/Enter = да, Esc = отмена)")
            with Horizontal(id="quit_actions"):
                yield Button("Остановить", variant="error", id="confirm_quit")
                yield Button("Отмена", id="cancel_quit")

    def on_mount(self) -> None:
        self.query_one("#confirm_quit", Button).focus()

    @on(Button.Pressed, "#confirm_quit")
    def _on_confirm_button(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel_quit")
    def _on_cancel_button(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
