#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Literal, Optional

from prompt_toolkit.application import Application
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit
from prompt_toolkit.shortcuts import message_dialog, radiolist_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Button, Dialog, Frame, Label, RadioList

from .backlog_status import BacklogStatus
from .task_source import Task

Mode = Literal["backlog", "single", "prompt"]


@dataclass(frozen=True)
class StartMenuChoice:
    mode: Mode
    task_id: str = ""
    prompt_text: str = ""
    debug_enabled: bool = False
    model: str = ""


def show_start_menu(backlog_status: BacklogStatus, *, models: list[str], default_model: str) -> StartMenuChoice:
    values = [
        ("backlog", "1) Выполнять задачи из backlog в цикле"),
        ("single", "2) Выполнить одну задачу из backlog"),
        ("prompt", "3) Выполнить произвольную задачу (textarea)"),
    ]

    while True:
        selected_mode, selected_model, debug_enabled = _pick_start_options(
            backlog_status=backlog_status,
            mode_values=values,
            models=models,
            default_model=default_model,
        )
        if selected_mode is None or selected_model is None:
            raise KeyboardInterrupt
        if selected_mode in {"backlog", "single"} and not backlog_status.has_open_tasks:
            message_dialog(
                title="Режим недоступен",
                text=f"Backlog-режим недоступен: {backlog_status.disabled_reason}",
            ).run()
            continue
        if selected_mode == "single":
            task = _pick_single_task(backlog_status.open_tasks)
            if task is None:
                continue
            return StartMenuChoice(
                mode="single",
                task_id=task.task_id,
                debug_enabled=debug_enabled,
                model=selected_model,
            )
        if selected_mode == "prompt":
            prompt_text = _read_prompt_textarea()
            return StartMenuChoice(
                mode="prompt",
                prompt_text=prompt_text,
                debug_enabled=debug_enabled,
                model=selected_model,
            )
        return StartMenuChoice(mode="backlog", debug_enabled=debug_enabled, model=selected_model)


def _menu_text(backlog_status: BacklogStatus) -> str:
    if backlog_status.has_open_tasks:
        return (
            f"Backlog: {backlog_status.path.name}\n"
            f"Открытых задач: {len(backlog_status.open_tasks)}\n"
            "Выберите режим и нажмите Enter."
        )
    return (
        f"Backlog: {backlog_status.path.name}\n"
        f"Backlog-пункты disabled: {backlog_status.disabled_reason}\n"
        "Доступен режим произвольной задачи."
    )


def _pick_single_task(open_tasks: list[Task]) -> Optional[Task]:
    values = [(task.task_id, f"{task.task_id} — {task.text}") for task in open_tasks]
    selected_id = radiolist_dialog(
        title="Выбор задачи",
        text="Выберите задачу из открытых пунктов BACKLOG.md",
        values=values,
    ).run()
    if selected_id is None:
        return None
    for task in open_tasks:
        if task.task_id == selected_id:
            return task
    return None


def _read_prompt_textarea() -> str:
    toolbar = "Textarea: Esc+Enter завершает ввод. Ctrl+C для отмены."
    while True:
        value = prompt("Prompt> ", multiline=True, bottom_toolbar=toolbar).strip()
        if value:
            return value
        message_dialog(title="Пустой ввод", text="Введите непустой prompt.").run()


def _pick_start_options(
    *,
    backlog_status: BacklogStatus,
    mode_values: list[tuple[str, str]],
    models: list[str],
    default_model: str,
) -> tuple[Optional[str], Optional[str], bool]:
    if not models:
        raise ValueError("models list must not be empty")

    mode_selector = RadioList(mode_values)
    mode_selector.current_value = mode_values[0][0]
    model_values = [(model, model) for model in models]
    model_selector = RadioList(model_values)
    model_selector.current_value = default_model if default_model in models else models[0]
    debug_selector = RadioList([("off", "Выключен"), ("on", "Включен")])
    debug_selector.current_value = "off"

    result: dict[str, Optional[str] | bool] = {"mode": None, "model": None, "debug": False}

    def accept() -> None:
        result["mode"] = mode_selector.current_value
        result["model"] = model_selector.current_value
        result["debug"] = debug_selector.current_value == "on"
        app.exit()

    def cancel() -> None:
        app.exit()

    left_column = HSplit(
        [
            Label(text=_menu_text(backlog_status)),
            Label(text=""),
            Label(text="Навигация: Tab/Shift+Tab между блоками, стрелки меняют выбор."),
            Label(text=""),
            Frame(
                title="Режим",
                body=mode_selector,
            ),
            Label(text=""),
            Frame(
                title="Debug logging",
                body=debug_selector,
            ),
        ]
    )
    right_column = HSplit(
        [
            Frame(
                title="Модель",
                body=model_selector,
            ),
            Label(text=""),
            Label(text=f"Default: {model_selector.current_value}"),
            Label(text="Выбранная модель будет сохранена как последняя ручная."),
        ]
    )
    body = VSplit(
        [
            Box(left_column, padding=1),
            Box(right_column, padding=1),
        ],
        padding=1,
    )
    dialog = Dialog(
        title="ORC стартовый экран",
        body=body,
        buttons=[Button(text="OK", handler=accept), Button(text="Cancel", handler=cancel)],
        with_background=True,
    )
    style = Style.from_dict(
        {
            "": "fg:#39ff14 bg:#0a0412",
            "dialog": "fg:#39ff14 bg:#0a0412",
            "dialog.body": "fg:#39ff14 bg:#0a0412",
            "dialog frame.label": "fg:#39ff14 bg:#0a0412 bold",
            "frame.border": "fg:#1c7f3a bg:#0a0412",
            "button": "fg:#39ff14 bg:#140a20",
            "button.focused": "fg:#0a0412 bg:#39ff14 bold",
            "radio": "fg:#39ff14 bg:#0a0412",
            "radio-selected": "fg:#39ff14 bg:#0a0412 bold",
            "label": "fg:#39ff14 bg:#0a0412",
        }
    )
    kb = KeyBindings()

    @kb.add("tab")
    def _focus_next(_event) -> None:
        _event.app.layout.focus_next()

    @kb.add("s-tab")
    def _focus_previous(_event) -> None:
        _event.app.layout.focus_previous()

    app = Application(
        layout=Layout(dialog, focused_element=mode_selector),
        key_bindings=kb,
        full_screen=True,
        style=style,
    )
    app.run()
    return (
        result["mode"] if isinstance(result["mode"], str) else None,
        result["model"] if isinstance(result["model"], str) else None,
        bool(result["debug"]),
    )
