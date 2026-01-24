#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from typing import Iterable, List, Optional, Tuple

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
OSC_RE = re.compile(r"\x1b\][^\x07]*(\x07|\x1b\\)")
CONTROL_RE = re.compile(r"[\x00-\x1F\x7F]")
TOKEN_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(k)?\s*tokens", re.IGNORECASE)
FILES_EDITED_RE = re.compile(r"(\d+)\s+files edited", re.IGNORECASE)
BOX_LINE_RE = re.compile(r"[┌┐└┘─│]")
NOISE_LINE_RE = re.compile(
    r"^(▶︎\s+Auto-run all commands|/ commands|.*ctrl\+c to stop.*)$",
    re.IGNORECASE,
)
STATUS_LINE_RE = re.compile(
    r"^(⬡\s+(Reading|Generating)\.|GPT-5\.2 Codex|/ commands|→ Add a follow-up)",
    re.IGNORECASE,
)
LIVE_STATUS_RE = re.compile(r"(⬡|⬢).+tokens", re.IGNORECASE)
COMMAND_RE_LIST = [
    re.compile(r"^\$\s+"),
    re.compile(r"^>\s+"),
    re.compile(r"^Running\s+command\b", re.IGNORECASE),
    re.compile(r"^Command\b", re.IGNORECASE),
    re.compile(r"^Executing\b", re.IGNORECASE),
]


def strip_ansi(text: str) -> str:
    without_osc = OSC_RE.sub("", text)
    without_ansi = ANSI_RE.sub("", without_osc)
    return CONTROL_RE.sub("", without_ansi)


def extract_tokens_from_line(line: str) -> Optional[int]:
    m = TOKEN_RE.search(line)
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    if m.group(2):
        value *= 1000.0
    return int(value)


def looks_like_command(line: str) -> bool:
    return any(regex.search(line) for regex in COMMAND_RE_LIST)


def extract_tokens_from_text(text: str) -> Optional[int]:
    return extract_tokens_from_line(text)


def extract_files_edited_from_text(text: str) -> Optional[int]:
    m = FILES_EDITED_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def clean_summary_lines(lines: Iterable[str]) -> List[str]:
    cleaned: List[str] = []
    for raw in lines:
        line = strip_ansi(raw).strip()
        if not line:
            continue
        if BOX_LINE_RE.search(line):
            continue
        if NOISE_LINE_RE.search(line):
            continue
        cleaned.append(line)
    return cleaned


def is_status_only_output(lines: Iterable[str]) -> bool:
    has_any = False
    for raw in lines:
        line = strip_ansi(raw).strip()
        if not line:
            continue
        has_any = True
        if BOX_LINE_RE.search(line):
            continue
        if NOISE_LINE_RE.search(line):
            continue
        if STATUS_LINE_RE.search(line):
            continue
        return False
    return has_any


def split_compacted_lines(text: str) -> List[str]:
    if not text:
        return []
    markers = [
        r"⬡\s",
        r"⬢\s",
        r"GPT-5\.2 Codex",
        r"/ commands",
        r"→ Add a follow-up",
        r"▶︎ Auto-run all commands",
        r"┌",
        r"└",
    ]
    pattern = "(" + "|".join(markers) + ")"
    parts = re.split(pattern, text)
    lines: List[str] = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts):
            segment = (parts[i] + parts[i + 1]).strip()
            if segment:
                lines.append(segment)
            i += 2
        else:
            tail = parts[i].strip()
            if tail:
                lines.append(tail)
            i += 1
    return lines


def extract_live_lines(lines: List[str]) -> Optional[Tuple[str, str]]:
    if not lines:
        return None
    status_idx = None
    for idx in range(len(lines) - 1, -1, -1):
        line = strip_ansi(lines[idx]).strip()
        if not line:
            continue
        if BOX_LINE_RE.search(line):
            continue
        if LIVE_STATUS_RE.search(line):
            status_idx = idx
            break
    if status_idx is None:
        return None
    status_line = strip_ansi(lines[status_idx]).strip()
    output_line = ""
    for j in range(status_idx - 1, -1, -1):
        candidate = strip_ansi(lines[j]).strip()
        if not candidate:
            continue
        if BOX_LINE_RE.search(candidate):
            continue
        output_line = candidate
        break
    return output_line, status_line
