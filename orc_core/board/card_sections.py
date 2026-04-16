#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured helpers for canonical kanban card body sections."""

from __future__ import annotations

from typing import Mapping

SECTION_PRODUCT = "# 1. Product Requirements"
SECTION_DESIGN = "# 2. Technical Design & DoD"
SECTION_NOTES = "# 3. Implementation Notes"
SECTION_FEEDBACK = "# 4. Feedback & Checklist"

SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("product_requirements", SECTION_PRODUCT),
    ("technical_design", SECTION_DESIGN),
    ("implementation_notes", SECTION_NOTES),
    ("feedback_checklist", SECTION_FEEDBACK),
)
SECTION_HEADERS = dict(SECTION_ORDER)
SECTION_KEYS = {header: key for key, header in SECTION_ORDER}


def new_card_body() -> str:
    """Return the canonical empty card body."""
    return render_card_sections({})


def parse_card_sections(body: str) -> dict[str, str]:
    """Parse card markdown into named section contents."""
    sections = {key: "" for key, _ in SECTION_ORDER}
    current_key = ""
    current_lines: list[str] = []
    preamble: list[str] = []

    for raw_line in body.splitlines():
        key = SECTION_KEYS.get(raw_line.strip())
        if key is not None:
            _flush_section(sections, current_key, current_lines, preamble)
            current_key = key
            current_lines = []
            continue
        if current_key:
            current_lines.append(raw_line)
        else:
            preamble.append(raw_line)

    _flush_section(sections, current_key, current_lines, preamble)
    if _has_known_header(body):
        return sections
    legacy = _normalize_lines(preamble)
    if legacy:
        sections["implementation_notes"] = legacy
    return sections


def render_card_sections(sections: Mapping[str, str]) -> str:
    """Render named sections into the canonical markdown layout."""
    parts: list[str] = []
    for key, header in SECTION_ORDER:
        text = str(sections.get(key, "") or "").strip()
        if text:
            parts.append(f"{header}\n\n{text}")
        else:
            parts.append(f"{header}\n")
    return "\n\n".join(parts).rstrip() + "\n"


def merge_section_updates(
    body: str,
    *,
    section_updates: Mapping[str, str] | None = None,
    feedback_append: str = "",
) -> str:
    """Apply structured section replacements plus feedback append."""
    sections = parse_card_sections(body)
    for key, value in (section_updates or {}).items():
        _ensure_known_key(key)
        sections[key] = str(value or "").strip()

    append_text = str(feedback_append or "").strip()
    if append_text:
        current = sections["feedback_checklist"]
        sections["feedback_checklist"] = (
            f"{current}\n\n{append_text}".strip() if current else append_text
        )
    return render_card_sections(sections)


def _flush_section(
    sections: dict[str, str],
    current_key: str,
    current_lines: list[str],
    preamble: list[str],
) -> None:
    if current_key:
        sections[current_key] = _normalize_lines(current_lines)
        return
    if preamble and _has_known_header("\n".join(preamble)):
        sections["product_requirements"] = _normalize_lines(preamble)
        preamble.clear()


def _ensure_known_key(key: str) -> None:
    if key not in SECTION_HEADERS:
        raise ValueError(f"Unknown card section key: {key}")


def _has_known_header(body: str) -> bool:
    return any(header in body for header in SECTION_KEYS)


def _normalize_lines(lines: list[str]) -> str:
    return "\n".join(lines).strip()
