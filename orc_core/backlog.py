#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import List, Optional

from .task_source import MarkdownTaskSource, Task


def is_task_done(path: Path, task_id: str) -> bool:
    return MarkdownTaskSource(path).is_task_done(task_id)


def parse_backlog(path: Path) -> List[Task]:
    return MarkdownTaskSource(path).list_tasks()


def find_first_open_task(path: Path) -> Optional[Task]:
    return MarkdownTaskSource(path).get_first_open_task()


def render_progress(done: int, total: int, width: int = 24) -> str:
    if total <= 0:
        total = 1
    ratio = min(max(done / total, 0.0), 1.0)
    filled = int(ratio * width)
    bar = "#" * filled + "." * (width - filled)
    pct = int(ratio * 100)
    return f"[{bar}] {done}/{total} {pct}%"
