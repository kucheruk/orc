#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

TASK_RE = re.compile(r"^\s*[-*]\s*\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$")
TASK_ID_RE = re.compile(
    r"(?:\*\*)?(?P<id>[A-Z][A-Z0-9_-]+)(?::)?(?:\*\*)?\s",
    re.UNICODE,
)


@dataclass
class Task:
    task_id: str
    text: str
    done: bool


def extract_task_id(text: str) -> Optional[str]:
    m = TASK_ID_RE.search(text)
    return m.group("id") if m else None


def is_task_done(path: Path, task_id: str) -> bool:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        if extract_task_id(text) == task_id:
            return m.group("mark").lower() == "x"
    return False


def parse_backlog(path: Path) -> List[Task]:
    tasks: List[Task] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        mark = m.group("mark")
        text = m.group("text").strip()
        task_id = extract_task_id(text)
        if not task_id:
            continue
        done = (mark.lower() == "x")
        tasks.append(Task(task_id=task_id, text=text, done=done))
    return tasks


def find_first_open_task(path: Path) -> Optional[Task]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        if m.group("mark") == " ":
            text = m.group("text").strip()
            task_id = extract_task_id(text)
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
