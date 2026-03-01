#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Switch, TextArea

from ...role_config import ALL_ROLE_IDS, RoleProfileRegistry
from .model_picker import ModelPickerModal


class PromptEditorModal(ModalScreen[Optional[str]]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, title: str, prompt_text: str) -> None:
        super().__init__()
        self._title = title
        self._prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        with Vertical(id="role_prompt_modal"):
            yield Label(f"Prompt: {self._title}")
            yield TextArea(self._prompt_text, id="role_prompt_editor")
            with Horizontal(id="role_prompt_actions"):
                yield Button("Сохранить", id="save_prompt", variant="primary")
                yield Button("Отмена", id="cancel_prompt")

    @on(Button.Pressed, "#save_prompt")
    def _on_save(self) -> None:
        editor = self.query_one("#role_prompt_editor", TextArea)
        self.dismiss(editor.text)

    @on(Button.Pressed, "#cancel_prompt")
    def _on_cancel_button(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class RoleSettingsModal(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(self, workdir: str, models: list[str], registry: Optional[RoleProfileRegistry] = None) -> None:
        super().__init__()
        self._workdir = workdir
        self._models = models
        self._registry = registry or RoleProfileRegistry()
        self._focus_before_model_picker_id = "close_roles"
        self._focus_before_prompt_editor_id = "close_roles"
        self._resolved = {role_id: self._registry.resolve_role(workdir, role_id) for role_id in ALL_ROLE_IDS}

    def compose(self) -> ComposeResult:
        with Vertical(id="role_settings_modal"):
            yield Label("Роли: сопоставление Role -> Model -> Prompt")
            for role_id in ALL_ROLE_IDS:
                role = self._resolved[role_id]
                with Horizontal(classes="role_row", id=f"role_row_{role_id}"):
                    yield Label(role.title, classes="role_title")
                    yield Switch(
                        value=role.enabled,
                        id=f"role_enabled_{role_id}",
                        disabled=not role.can_toggle_enabled,
                    )
                    yield Label(role.model, id=f"role_model_value_{role_id}", classes="role_model")
                    yield Button("Model", id=f"role_model_pick_{role_id}")
                    yield Button("Prompt", id=f"role_prompt_edit_{role_id}")
            with Horizontal(id="role_settings_actions"):
                yield Button("Закрыть", id="close_roles", variant="primary")

    @on(Button.Pressed, "#close_roles")
    def _on_close(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id or "")
        if button_id.startswith("role_model_pick_"):
            role_id = button_id.removeprefix("role_model_pick_")
            role = self._resolved.get(role_id)
            if role is None:
                return
            self._focus_before_model_picker_id = button_id
            self.push_screen(
                ModelPickerModal(models=self._models, selected_model=role.model),
                lambda selected: self._on_model_selected(role_id, selected),
            )
            return
        if button_id.startswith("role_prompt_edit_"):
            role_id = button_id.removeprefix("role_prompt_edit_")
            role = self._resolved.get(role_id)
            if role is None:
                return
            self._focus_before_prompt_editor_id = button_id
            self.push_screen(
                PromptEditorModal(role.title, role.prompt),
                lambda prompt_text: self._on_prompt_updated(role_id, prompt_text),
            )

    @on(Switch.Changed)
    def _on_enabled_changed(self, event: Switch.Changed) -> None:
        switch_id = str(event.switch.id or "")
        if not switch_id.startswith("role_enabled_"):
            return
        role_id = switch_id.removeprefix("role_enabled_")
        role = self._resolved.get(role_id)
        if role is None or not role.can_toggle_enabled:
            return
        self._registry.update_override(self._workdir, role_id, enabled=bool(event.value))
        self._resolved[role_id] = self._registry.resolve_role(self._workdir, role_id)

    def _on_model_selected(self, role_id: str, selected_model: Optional[str]) -> None:
        if selected_model:
            self._registry.update_override(self._workdir, role_id, model=selected_model)
            self._resolved[role_id] = self._registry.resolve_role(self._workdir, role_id)
            self._update_role_row(role_id)
        self.set_focus(self.query_one(f"#{self._focus_before_model_picker_id}"))

    def _on_prompt_updated(self, role_id: str, prompt_text: Optional[str]) -> None:
        if prompt_text is not None:
            self._registry.update_override(self._workdir, role_id, prompt=prompt_text)
            self._resolved[role_id] = self._registry.resolve_role(self._workdir, role_id)
            self._update_role_row(role_id)
        self.set_focus(self.query_one(f"#{self._focus_before_prompt_editor_id}"))

    def _update_role_row(self, role_id: str) -> None:
        role = self._resolved[role_id]
        self.query_one(f"#role_model_value_{role_id}", Label).update(role.model)
        enabled_switch = self.query_one(f"#role_enabled_{role_id}", Switch)
        enabled_switch.value = role.enabled
        enabled_switch.disabled = not role.can_toggle_enabled

    def action_cancel(self) -> None:
        self.dismiss(False)
