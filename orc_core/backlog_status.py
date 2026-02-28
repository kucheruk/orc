#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from pathlib import Path

from .task_source import MarkdownTaskSource, Task


@dataclass(frozen=True)
class BacklogStatus:
    path: Path
    exists: bool
    tasks: list[Task]
    open_tasks: list[Task]

    @property
    def has_tasks(self) -> bool:
        return bool(self.tasks)

    @property
    def has_open_tasks(self) -> bool:
        return bool(self.open_tasks)

    @property
    def disabled_reason(self) -> str:
        if not self.exists:
            return f"Файл не найден: {self.path.name}"
        if not self.tasks:
            return "В backlog нет валидных задач с ID"
        if not self.open_tasks:
            return "В backlog нет открытых задач"
        return ""


def inspect_backlog(path: Path) -> BacklogStatus:
    if not path.exists():
        return BacklogStatus(path=path, exists=False, tasks=[], open_tasks=[])
    source = MarkdownTaskSource(path)
    tasks = source.list_tasks()
    open_tasks = [task for task in tasks if not task.done]
    return BacklogStatus(path=path, exists=True, tasks=tasks, open_tasks=open_tasks)
