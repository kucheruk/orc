#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Switch

from ...backlog_status import BacklogStatus
from ...start_menu import StartMenuChoice


class StartMenuScreen(Screen[StartMenuChoice]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        backlog_status: BacklogStatus,
        models: list[str],
        default_model: str,
        resume_task_id: str = "",
        status_line: str = "",
    ) -> None:
        super().__init__()
        self._backlog_status = backlog_status
        self._models = list(models)
        self._default_model = default_model if default_model in models else models[0]
        self._resume_task_id = resume_task_id.strip()
        self._status_line = status_line.strip()
        self._mode_values = [
            ("backlog", "Выполнять задачи из backlog в цикле"),
            ("single", "Выполнить одну задачу из backlog"),
            ("prompt", "Выполнить произвольную задачу"),
        ]
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
                    yield Label("Task ID (для single)")
                    yield Label(self._available_task_ids_hint(), id="task_ids_hint", classes="help")
                    default_task = self._backlog_status.open_tasks[0].task_id if self._backlog_status.open_tasks else ""
                    yield Input(value=default_task, id="task_id")
                    yield Label("Нажмите Enter в поле Task ID или Prompt, чтобы запустить.", id="submit_hint", classes="help")
                    yield Label("Prompt (для prompt)")
                    yield Input(placeholder="Введите prompt", id="prompt_text")
                with Vertical(classes="col"):
                    yield Label("Модель")
                    with RadioSet(id="model_set"):
                        for idx, model in enumerate(self._models):
                            yield RadioButton(model, value=model == self._default_model, id=f"model_{idx}")
                    yield Label("Enter — запустить, Esc — отмена", classes="help")
            with Horizontal(id="menu_actions"):
                yield Button("Запустить", id="start_btn", variant="primary")
                yield Button("Отмена", id="cancel_btn", variant="default")
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

    def _selected_model(self) -> str:
        selected = self.query_one("#model_set", RadioSet).pressed_index
        if selected is None:
            return self._default_model
        return self._models[selected]

    def _set_error(self, message: str) -> None:
        self.query_one("#error_text", Label).update(f"[red]{message}[/red]")

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
        return StartMenuChoice(
            mode=mode,
            task_id=task_id,
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

    def action_cancel(self) -> None:
        self.dismiss(None)  # type: ignore[arg-type]
