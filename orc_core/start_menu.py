#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass


@dataclass(frozen=True)
class StartMenuChoice:
    mode: str = "kanban"
    task_id: str = ""
    prompt_text: str = ""
    debug_enabled: bool = False
    model: str = ""
