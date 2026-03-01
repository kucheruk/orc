#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Literal

from .backlog_status import BacklogStatus

Mode = Literal["backlog", "single", "prompt"]


@dataclass(frozen=True)
class StartMenuChoice:
    mode: Mode
    task_id: str = ""
    prompt_text: str = ""
    debug_enabled: bool = False
    model: str = ""


def show_start_menu(backlog_status: BacklogStatus, *, models: list[str], default_model: str) -> StartMenuChoice:
    from .tui_app import run_start_menu

    choice = run_start_menu(backlog_status, models=models, default_model=default_model)
    if choice is None:
        raise KeyboardInterrupt
    return choice
