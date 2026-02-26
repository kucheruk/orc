#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass
from typing import Optional

TASK_LINE_RE = re.compile(
    r"^(?P<prefix>\s*[-*]\s*\[)(?P<mark>[ xX])(?P<suffix>\]\s+)(?P<text>.+?)\s*$"
)
TASK_ID_RE = re.compile(
    r"(?:\*\*)?(?P<id>[A-Z][A-Z0-9_-]+)(?::)?(?:\*\*)?\s",
    re.UNICODE,
)


@dataclass(frozen=True)
class ParsedTaskLine:
    prefix: str
    mark: str
    suffix: str
    text: str
    task_id: Optional[str]


def extract_task_id(text: str) -> Optional[str]:
    match = TASK_ID_RE.search(text)
    return match.group("id") if match else None


def parse_task_line(line: str) -> Optional[ParsedTaskLine]:
    match = TASK_LINE_RE.match(line)
    if not match:
        return None
    text = match.group("text").strip()
    return ParsedTaskLine(
        prefix=match.group("prefix"),
        mark=match.group("mark"),
        suffix=match.group("suffix"),
        text=text,
        task_id=extract_task_id(text),
    )


def render_task_line_with_mark(task_line: ParsedTaskLine, mark: str) -> str:
    normalized_mark = "x" if str(mark).lower() == "x" else " "
    return f"{task_line.prefix}{normalized_mark}{task_line.suffix}{task_line.text}"
