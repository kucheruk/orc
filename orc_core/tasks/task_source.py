#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import List, Optional, Protocol

from ..board.backlog_markdown_parser import mark_task_done_in_lines, parse_backlog_markdown
from .task_dto import Task


class TaskSource(Protocol):
    def list_tasks(self) -> List[Task]:
        ...

    def get_open_tasks(self) -> List[Task]:
        ...

    def get_first_open_task(self) -> Optional[Task]:
        ...

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        ...

    def is_task_done(self, task_id: str) -> bool:
        ...

    def mark_task_done(self, task_id: str) -> bool:
        ...


class MarkdownTaskSource:
    def __init__(self, path: Path):
        self.path = path

    def list_tasks(self) -> List[Task]:
        raw = self.path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_backlog_markdown(raw)
        return [Task(task_id=item.task_id, text=item.text, done=item.done) for item in parsed]

    def get_first_open_task(self) -> Optional[Task]:
        for task in self.list_tasks():
            if not task.done:
                return task
        return None

    def get_open_tasks(self) -> List[Task]:
        return [task for task in self.list_tasks() if not task.done]

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        wanted = str(task_id or "").strip()
        if not wanted:
            return None
        first_done: Optional[Task] = None
        for task in self.list_tasks():
            if task.task_id != wanted:
                continue
            if not task.done:
                return task
            if first_done is None:
                first_done = task
        return first_done

    def is_task_done(self, task_id: str) -> bool:
        found = False
        for task in self.list_tasks():
            if task.task_id != task_id:
                continue
            found = True
            if not task.done:
                return False
        return found

    def mark_task_done(self, task_id: str) -> bool:
        content = self.path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        parsed = parse_backlog_markdown(content)
        found, changed = mark_task_done_in_lines(lines, task_id, parsed)
        if found and changed:
            self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return found
