#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .task_contract import parse_task_line


@dataclass
class Task:
    task_id: str
    text: str
    done: bool


def is_task_done(path: Path, task_id: str) -> bool:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = parse_task_line(line)
        if not parsed:
            continue
        if parsed.task_id == task_id:
            return parsed.mark.lower() == "x"
    return False


def parse_backlog(path: Path) -> List[Task]:
    tasks: List[Task] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = parse_task_line(line)
        if not parsed:
            continue
        mark = parsed.mark
        text = parsed.text
        task_id = parsed.task_id
        if not task_id:
            continue
        done = (mark.lower() == "x")
        tasks.append(Task(task_id=task_id, text=text, done=done))
    return tasks


def find_first_open_task(path: Path) -> Optional[Task]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = parse_task_line(line)
        if not parsed:
            continue
        if parsed.mark == " ":
            text = parsed.text
            task_id = parsed.task_id
            if not task_id:
                continue
            return Task(task_id=task_id, text=text, done=False)
    return None


def render_progress(done: int, total: int, width: int = 24) -> str:
    if total <= 0:
        total = 1
    ratio = min(max(done / total, 0.0), 1.0)
    filled = int(ratio * width)
    bar = "#" * filled + "." * (width - filled)
    pct = int(ratio * 100)
    return f"[{bar}] {done}/{total} {pct}%"
