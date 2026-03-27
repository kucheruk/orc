#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Switch

from ...backlog_status import BacklogStatus
from ...role_config import ROLE_CODER, RoleProfileRegistry
from ...start_menu import StartMenuChoice
from .model_picker import ModelPickerModal
from .role_settings import RoleSettingsModal


class StartMenuScreen(Screen[StartMenuChoice]):
    BINDINGS = [
        ("tab", "tab_cycle_forward", "Next"),
        ("shift+tab", "tab_cycle_backward", "Previous"),
        ("f2", "open_model_picker", "Model"),
        ("f3", "open_role_settings", "Roles"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        backlog_status: BacklogStatus,
        models: list[str],
        default_model: str,
        resume_task_id: str = "",
        status_line: str = "",
        workdir: str = "",
        role_registry: Optional[RoleProfileRegistry] = None,
    ) -> None:
        super().__init__()
        self._backlog_status = backlog_status
        self._models = list(models)
        self._default_model = default_model if default_model in models else models[0]
        self._selected_model_value = self._default_model
        self._resume_task_id = resume_task_id.strip()
        self._status_line = status_line.strip()
        self._workdir = workdir
        self._role_registry = role_registry or RoleProfileRegistry()
        self._focus_before_model_modal_id = "mode_set"
        self._focus_before_roles_modal_id = "roles_btn"
        self._mode_values = [
            ("backlog", "Выполнять задачи из backlog в цикле"),
            ("single", "Выполнить одну задачу из backlog"),
            ("prompt", "Выполнить произвольную задачу"),
        ]
        self._sync_model_from_coder_role()
        if self._resume_task_id:
            self._mode_values.insert(0, ("resume", f"Продолжить текущую задачу ({self._resume_task_id})"))

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="menu_root"):
            yield Label(self._menu_text(), id="menu_text")
            if self._status_line:
                yield Label(f"[green]{self._status_line}[/green]", id="status_line")
            with Horizontal(id="menu_cols"):
                with Vertical(classes="col"):
                    yield Label("Режим")
                    with RadioSet(id="mode_set"):
                        for idx, (_value, title) in enumerate(self._mode_values):
                            yield RadioButton(title, value=idx == 0, id=f"mode_{idx}")
                    yield Label("Debug logging")
                    yield Switch(value=True, id="debug_switch")
                    yield Label("Task ID (для single)", id="task_id_label")
                    yield Label(self._available_task_ids_hint(), id="task_ids_hint", classes="help")
                    default_task = self._backlog_status.open_tasks[0].task_id if self._backlog_status.open_tasks else ""
                    yield Input(value=default_task, id="task_id")
                    yield Label("Нажмите Enter в поле ввода, чтобы запустить.", id="submit_hint", classes="help")
                    yield Label("Prompt (для prompt)", id="prompt_label")
                    yield Input(placeholder="Введите prompt", id="prompt_text")
                with Vertical(classes="col"):
                    yield Label("Модель")
                    yield Label("", id="model_value")
                    yield Label("F2 — выбор модели, F3 — роли", classes="help")
                    yield Button("Roles (F3)", id="roles_btn", variant="default")
                    yield Label("Enter — запустить, Esc — выйти", classes="help")
            with Horizontal(id="menu_actions"):
                yield Button("Запустить", id="start_btn", variant="primary")
                yield Button("Выйти", id="cancel_btn", variant="default")
            yield Label("", id="error_text")
        yield Footer()

    def _menu_text(self) -> str:
        if self._backlog_status.has_open_tasks:
            return (
                f"Backlog: {self._backlog_status.path.name} | "
                f"Открытых задач: {len(self._backlog_status.open_tasks)}"
            )
        return (
            f"Backlog: {self._backlog_status.path.name} | "
            f"Backlog-пункты disabled: {self._backlog_status.disabled_reason}"
        )

    def _available_task_ids_hint(self) -> str:
        open_tasks = self._backlog_status.open_tasks
        if not open_tasks:
            return "Нет открытых задач. Для режимов backlog/single нужен backlog с незавершёнными задачами."
        preview_limit = 8
        task_ids = ", ".join(task.task_id for task in open_tasks[:preview_limit])
        remaining = len(open_tasks) - preview_limit
        if remaining > 0:
            return f"Открытые ID: {task_ids} (+{remaining})"
        return f"Открытые ID: {task_ids}"

    def _selected_mode(self) -> str:
        selected = self.query_one("#mode_set", RadioSet).pressed_index
        return self._mode_values[selected if selected is not None else 0][0]

    def _is_task_input_visible(self, mode: str) -> bool:
        return mode == "single"

    def _is_prompt_input_visible(self, mode: str) -> bool:
        return mode == "prompt"

    def _focus_cycle_for_mode(self, mode: str) -> list[str]:
        focus_cycle = ["mode_set"]
        if self._is_task_input_visible(mode):
            focus_cycle.append("task_id")
        elif self._is_prompt_input_visible(mode):
            focus_cycle.append("prompt_text")
        focus_cycle.extend(["roles_btn", "start_btn", "cancel_btn"])
        return focus_cycle

    def _selected_model(self) -> str:
        return self._selected_model_value

    def _set_error(self, message: str) -> None:
        safe_message = message.replace("[", r"\[")
        self.query_one("#error_text", Label).update(f"[red]{safe_message}[/red]")

    def _set_visible(self, widget_id: str, is_visible: bool) -> None:
        widget = self.query_one(f"#{widget_id}")
        widget.display = is_visible

    def _update_selected_model_label(self) -> None:
        self.query_one("#model_value", Label).update(f"{self._selected_model_value} (F2)")

    def _sync_model_from_coder_role(self) -> None:
        if not self._workdir:
            return
        resolved = self._role_registry.resolve_role(self._workdir, ROLE_CODER)
        if resolved.model in self._models:
            self._selected_model_value = resolved.model

    def _apply_mode_visibility(self) -> None:
        mode = self._selected_mode()
        task_visible = self._is_task_input_visible(mode)
        prompt_visible = self._is_prompt_input_visible(mode)

        self._set_visible("task_id_label", task_visible)
        self._set_visible("task_ids_hint", task_visible)
        self._set_visible("task_id", task_visible)
        self._set_visible("prompt_label", prompt_visible)
        self._set_visible("prompt_text", prompt_visible)
        self._set_visible("submit_hint", task_visible or prompt_visible)

    def _cycle_focus(self, forward: bool) -> None:
        focus_cycle = self._focus_cycle_for_mode(self._selected_mode())
        focused_id = self._focused_cycle_id(focus_cycle)

        if focused_id not in focus_cycle:
            target_id = focus_cycle[0] if forward else focus_cycle[-1]
        else:
            index = focus_cycle.index(focused_id)
            target_id = focus_cycle[(index + 1) % len(focus_cycle)] if forward else focus_cycle[(index - 1) % len(focus_cycle)]

        self.set_focus(self.query_one(f"#{target_id}"))

    def _focused_cycle_id(self, focus_cycle: list[str]) -> Optional[str]:
        focused = self.app.focused
        if focused is None:
            return None
        current: Optional[Widget] = focused
        while current is not None:
            if current.id in focus_cycle:
                return current.id
            current = current.parent
        return None

    def _ensure_focus_visible(self) -> None:
        focus_cycle = self._focus_cycle_for_mode(self._selected_mode())
        focused_id = self._focused_cycle_id(focus_cycle)
        if focused_id is None or focused_id not in focus_cycle:
            self.set_focus(self.query_one(f"#{focus_cycle[0]}"))

    def _build_choice(self) -> Optional[StartMenuChoice]:
        mode = self._selected_mode()
        model = self._selected_model()
        debug_enabled = self.query_one("#debug_switch", Switch).value
        task_id = self.query_one("#task_id", Input).value.strip()
        prompt_text = self.query_one("#prompt_text", Input).value.strip()

        if mode in {"backlog", "single"} and not self._backlog_status.has_open_tasks:
            self._set_error(f"Backlog-режим недоступен: {self._backlog_status.disabled_reason}")
            return None
        if mode == "resume":
            if not self._resume_task_id:
                self._set_error("Resume mode недоступен: не найдена активная задача.")
                return None
            return StartMenuChoice(
                mode="resume",
                task_id=self._resume_task_id,
                debug_enabled=debug_enabled,
                model=model,
            )
        if mode == "single" and not task_id and self._backlog_status.open_tasks:
            task_id = self._backlog_status.open_tasks[0].task_id
        if mode == "single" and not task_id:
            self._set_error("Single mode требует task id.")
            return None
        if mode == "prompt" and not prompt_text:
            self._set_error("Prompt mode требует непустой prompt.")
            return None
        result_task_id = task_id if mode == "single" else ""
        return StartMenuChoice(
            mode=mode,
            task_id=result_task_id,
            prompt_text=prompt_text,
            debug_enabled=debug_enabled,
            model=model,
        )

    @on(Button.Pressed, "#start_btn")
    def _on_start(self) -> None:
        choice = self._build_choice()
        if choice is not None:
            self.dismiss(choice)

    @on(Button.Pressed, "#cancel_btn")
    def _on_cancel_btn(self) -> None:
        self.action_cancel()

    @on(Input.Submitted, "#prompt_text")
    @on(Input.Submitted, "#task_id")
    def _on_submit(self) -> None:
        self._on_start()

    @on(RadioSet.Changed, "#mode_set")
    def _on_mode_changed(self) -> None:
        self._apply_mode_visibility()
        self._ensure_focus_visible()

    def on_mount(self) -> None:
        self._apply_mode_visibility()
        self._update_selected_model_label()
        self.query_one("#debug_switch", Switch).can_focus = False
        self.set_focus(self.query_one("#mode_set"))

    def action_tab_cycle_forward(self) -> None:
        self._cycle_focus(forward=True)

    def action_tab_cycle_backward(self) -> None:
        self._cycle_focus(forward=False)

    def action_open_model_picker(self) -> None:
        focus_cycle = self._focus_cycle_for_mode(self._selected_mode())
        focused_id = self._focused_cycle_id(focus_cycle)
        self._focus_before_model_modal_id = focused_id if focused_id is not None else focus_cycle[0]
        self.app.push_screen(
            ModelPickerModal(models=self._models, selected_model=self._selected_model_value),
            self._on_model_picker_closed,
        )

    def _on_model_picker_closed(self, selected_model: Optional[str]) -> None:
        if selected_model:
            self._selected_model_value = selected_model
            self._update_selected_model_label()
        self.set_focus(self.query_one(f"#{self._focus_before_model_modal_id}"))

    @on(Button.Pressed, "#roles_btn")
    def _on_open_roles_btn(self) -> None:
        self.action_open_role_settings()

    def action_open_role_settings(self) -> None:
        focus_cycle = self._focus_cycle_for_mode(self._selected_mode())
        focused_id = self._focused_cycle_id(focus_cycle)
        self._focus_before_roles_modal_id = focused_id if focused_id is not None else "roles_btn"
        self.app.push_screen(
            RoleSettingsModal(workdir=self._workdir, models=self._models, registry=self._role_registry),
            self._on_role_settings_closed,
        )

    def _on_role_settings_closed(self, _saved: bool) -> None:
        self._sync_model_from_coder_role()
        self._update_selected_model_label()
        self.set_focus(self.query_one(f"#{self._focus_before_roles_modal_id}"))

    def action_cancel(self) -> None:
        self.dismiss(None)  # type: ignore[arg-type]
