#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Literal, Optional

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import message_dialog, radiolist_dialog

from .backlog_status import BacklogStatus
from .task_source import Task

Mode = Literal["backlog", "single", "prompt"]


@dataclass(frozen=True)
class StartMenuChoice:
    mode: Mode
    task_id: str = ""
    prompt_text: str = ""
    debug_enabled: bool = False


def show_start_menu(backlog_status: BacklogStatus) -> StartMenuChoice:
    values = [
        ("backlog", "1) Выполнять задачи из backlog в цикле"),
        ("single", "2) Выполнить одну задачу из backlog"),
        ("prompt", "3) Выполнить произвольную задачу (textarea)"),
    ]

    while True:
        selected_mode = radiolist_dialog(
            title="ORC стартовый режим",
            text=_menu_text(backlog_status),
            values=values,
        ).run()
        if selected_mode is None:
            raise KeyboardInterrupt
        if selected_mode in {"backlog", "single"} and not backlog_status.has_open_tasks:
            message_dialog(
                title="Режим недоступен",
                text=f"Backlog-режим недоступен: {backlog_status.disabled_reason}",
            ).run()
            continue
        debug_enabled = _pick_debug_enabled()
        if selected_mode == "single":
            task = _pick_single_task(backlog_status.open_tasks)
            if task is None:
                continue
            return StartMenuChoice(mode="single", task_id=task.task_id, debug_enabled=debug_enabled)
        if selected_mode == "prompt":
            prompt_text = _read_prompt_textarea()
            return StartMenuChoice(mode="prompt", prompt_text=prompt_text, debug_enabled=debug_enabled)
        return StartMenuChoice(mode="backlog", debug_enabled=debug_enabled)


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


def _pick_debug_enabled() -> bool:
    selected = radiolist_dialog(
        title="Дополнительные опции",
        text="Debug logging в /tmp/orc:",
        values=[
            ("off", "Выключен"),
            ("on", "Включен"),
        ],
        default="off",
    ).run()
    return selected == "on"
