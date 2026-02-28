#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol

from .task_contract import parse_task_line, render_task_line_with_mark


@dataclass(frozen=True)
class Task:
    task_id: str
    text: str
    done: bool


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
        tasks: List[Task] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            parsed = parse_task_line(line)
            if not parsed or not parsed.task_id:
                continue
            tasks.append(
                Task(
                    task_id=parsed.task_id,
                    text=parsed.text,
                    done=parsed.mark.lower() == "x",
                )
            )
        return tasks

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
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        found = False
        changed = False
        for i, line in enumerate(lines):
            parsed = parse_task_line(line)
            if not parsed or parsed.task_id != task_id:
                continue
            found = True
            if parsed.mark.lower() == "x":
                continue
            lines[i] = render_task_line_with_mark(parsed, "x")
            changed = True
        if found and changed:
            self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return found
