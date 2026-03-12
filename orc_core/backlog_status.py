#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from pathlib import Path

from .backlog_markdown_parser import find_open_tasks_in_markdown_fences
from .task_source import MarkdownTaskSource, Task


@dataclass(frozen=True)
class BacklogStatus:
    path: Path
    exists: bool
    tasks: list[Task]
    open_tasks: list[Task]
    hidden_open_tasks: list[Task] = field(default_factory=list)

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
        if self.hidden_open_tasks:
            sample_ids = ", ".join(task.task_id for task in self.hidden_open_tasks[:3])
            suffix = "" if len(self.hidden_open_tasks) <= 3 else ", ..."
            return (
                "Открытые задачи найдены внутри fenced блока ```markdown```: "
                f"{sample_ids}{suffix}. Вынесите их из code fence в обычный список backlog."
            )
        if not self.tasks:
            return "В backlog нет валидных задач с ID"
        if not self.open_tasks:
            return "В backlog нет открытых задач"
        return ""


def inspect_backlog(path: Path) -> BacklogStatus:
    if not path.exists():
        return BacklogStatus(path=path, exists=False, tasks=[], open_tasks=[])
    raw = path.read_text(encoding="utf-8", errors="replace")
    source = MarkdownTaskSource(path)
    tasks = source.list_tasks()
    open_tasks = [task for task in tasks if not task.done]
    hidden_open_tasks = []
    if not open_tasks:
        hidden_open_tasks = [
            Task(task_id=item.task_id, text=item.text, done=item.done)
            for item in find_open_tasks_in_markdown_fences(raw)
        ]
    return BacklogStatus(
        path=path,
        exists=True,
        tasks=tasks,
        open_tasks=open_tasks,
        hidden_open_tasks=hidden_open_tasks,
    )
