#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serialization for `KanbanCard` — markdown ↔ dataclass.

Split out of `kanban_card.py` so the domain aggregate stays free of
storage-format concerns. Callers that persist, render, or parse cards
depend on this module; `KanbanCard` itself only enforces invariants and
exposes domain operations.
"""
from __future__ import annotations

from dataclasses import fields as _dc_fields
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .action_constants import Action
from .kanban_card import _RUNTIME_FIELDS, KanbanCard
from ..text_parse import parse_frontmatter


def card_to_markdown(card: KanbanCard) -> str:
    fm = _build_frontmatter(card)
    return f"---\n{fm}---\n\n{card.body}"


def card_to_frontmatter_dict(card: KanbanCard) -> dict[str, Any]:
    """Build YAML-serializable dict from dataclass fields (SSOT)."""
    result: dict[str, Any] = {}
    for f in _dc_fields(card):
        if f.name in _RUNTIME_FIELDS:
            continue
        val = getattr(card, f.name)
        if isinstance(val, list):
            val = [str(v) for v in val]
        elif isinstance(val, Enum):
            val = val.value
        result[f.name] = val
    return result


def parse_card(text: str, file_path: Path | None = None) -> KanbanCard:
    data, body = parse_frontmatter(text, str(file_path or "<string>"))
    defaults = KanbanCard(id="")
    kwargs: dict[str, Any] = {"body": body, "file_path": file_path}
    for f in _dc_fields(defaults):
        if f.name in _RUNTIME_FIELDS:
            continue
        default_val = getattr(defaults, f.name)
        raw = data.get(f.name, default_val)
        if f.name == "action":
            kwargs[f.name] = _normalize_action(raw)
        elif f.name == "dependencies":
            kwargs[f.name] = _parse_list(raw)
        elif isinstance(default_val, int):
            kwargs[f.name] = int(raw or 0)
        elif isinstance(default_val, float):
            kwargs[f.name] = float(raw or 0.0)
        else:
            kwargs[f.name] = str(raw or "")
    return KanbanCard(**kwargs)


def _build_frontmatter(card: KanbanCard) -> str:
    return yaml.dump(
        card_to_frontmatter_dict(card),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def _normalize_action(raw: str) -> str:
    s = str(raw).strip()
    if not s:
        return Action.PRODUCT
    try:
        return Action(s)
    except ValueError:
        pass
    for member in Action:
        if member.value.lower() == s.lower():
            return member.value
    return s


def _parse_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    s = str(val)
    if "," in s:
        return [part.strip() for part in s.split(",") if part.strip()]
    s = s.strip()
    return [s] if s else []
