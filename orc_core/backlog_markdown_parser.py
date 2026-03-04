#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass
from typing import Sequence

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .task_contract import extract_task_id

CHECKBOX_TEXT_RE = re.compile(r"^\[(?P<mark>[ xX])\]\s*(?P<text>.*)$", re.UNICODE)
LIST_ITEM_CHECKBOX_RE = re.compile(r"^\s*[-+*]\s*\[[ xX]\]")
CHECKBOX_MARK_RE = re.compile(r"^(?P<prefix>\s*[-+*]\s*\[)(?P<mark>[ xX])(?P<suffix>\])")
TASK_REPORT_MARKER_RE = re.compile(r"(?:→|->)\s*tasks/(?P<task_id>[A-Za-z0-9_-]+)\.md\b", re.UNICODE)


@dataclass(frozen=True)
class ParsedBacklogTask:
    task_id: str
    text: str
    done: bool
    line_index: int


def parse_backlog_markdown(markdown_text: str) -> list[ParsedBacklogTask]:
    lines = markdown_text.splitlines()
    parser = MarkdownIt("commonmark")
    tokens = parser.parse(markdown_text)
    tasks: list[ParsedBacklogTask] = []
    for index, token in enumerate(tokens):
        if token.type != "list_item_open":
            continue
        if not token.map:
            continue
        start, end = token.map
        close_index = _find_list_item_close(tokens, index)
        if close_index <= index:
            continue
        checkbox = _find_checkbox_payload(tokens, index + 1, close_index)
        if checkbox is None:
            continue
        mark, task_text = checkbox
        task_id = extract_task_id(task_text)
        if not task_id:
            continue
        line_index = _find_checkbox_line(lines, start, end)
        if line_index is None:
            continue
        tasks.append(
            ParsedBacklogTask(
                task_id=task_id,
                text=task_text,
                done=(mark.lower() == "x") or _has_task_report_marker(task_text, task_id),
                line_index=line_index,
            )
        )
    return tasks


def mark_task_done_in_lines(lines: list[str], task_id: str, tasks: Sequence[ParsedBacklogTask]) -> tuple[bool, bool]:
    wanted = str(task_id or "").strip()
    if not wanted:
        return False, False
    found = False
    changed = False
    for task in tasks:
        if task.task_id != wanted:
            continue
        found = True
        if task.done:
            continue
        line = lines[task.line_index]
        updated = CHECKBOX_MARK_RE.sub(r"\g<prefix>x\g<suffix>", line, count=1)
        if updated != line:
            lines[task.line_index] = updated
            changed = True
    return found, changed


def _find_list_item_close(tokens: Sequence[Token], start_index: int) -> int:
    depth = 0
    for index in range(start_index, len(tokens)):
        token = tokens[index]
        if token.type == "list_item_open":
            depth += 1
            continue
        if token.type == "list_item_close":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _find_checkbox_payload(tokens: Sequence[Token], start: int, end: int) -> tuple[str, str] | None:
    for index in range(start, end):
        token = tokens[index]
        if token.type != "inline":
            continue
        visible_text = _inline_visible_text(token).strip()
        match = CHECKBOX_TEXT_RE.match(visible_text)
        if not match:
            continue
        text = match.group("text").strip()
        return match.group("mark"), text
    return None


def _inline_visible_text(inline_token: Token) -> str:
    children = inline_token.children or []
    if not children:
        return inline_token.content or ""
    chunks: list[str] = []
    for child in children:
        if child.type in {"text", "code_inline"}:
            chunks.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            chunks.append(" ")
    return "".join(chunks)


def _find_checkbox_line(lines: Sequence[str], start: int, end: int) -> int | None:
    start_line = max(start, 0)
    end_line = min(max(end, start_line), len(lines))
    for line_index in range(start_line, end_line):
        if LIST_ITEM_CHECKBOX_RE.match(lines[line_index]):
            return line_index
    return None


def _has_task_report_marker(task_text: str, task_id: str) -> bool:
    for match in TASK_REPORT_MARKER_RE.finditer(task_text):
        if match.group("task_id") == task_id:
            return True
    return False
