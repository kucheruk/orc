#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead decision file: data model and YAML frontmatter parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ....text_parse import parse_frontmatter

DECISION_FILENAME = "teamlead-decision.md"


@dataclass
class TeamleadAction:
    type: str
    params: dict[str, Any]
    reason: str = ""


@dataclass
class TeamleadDecision:
    actions: list[TeamleadAction] = field(default_factory=list)
    summary: str = ""


def decision_path(workdir: str) -> Path:
    """Return the standard decision file path for a workdir."""
    p = Path(workdir) / ".orc"
    p.mkdir(parents=True, exist_ok=True)
    return p / DECISION_FILENAME


def parse_teamlead_decision(path: Path) -> TeamleadDecision:
    """Parse a teamlead decision file. Raises ValueError on bad format."""
    text = path.read_text(encoding="utf-8")
    data, _ = parse_frontmatter(text, str(path))

    summary = str(data.get("summary", "")).strip()
    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list):
        raise ValueError(f"'actions' must be a list, got {type(raw_actions).__name__}")

    actions: list[TeamleadAction] = []
    for i, raw in enumerate(raw_actions):
        if not isinstance(raw, dict):
            raise ValueError(f"Action #{i} is not a dict")
        action_type = str(raw.get("type", "")).strip()
        if not action_type:
            raise ValueError(f"Action #{i} missing 'type'")
        reason = str(raw.get("reason", "")).strip()
        params = {k: v for k, v in raw.items() if k not in ("type", "reason")}
        actions.append(TeamleadAction(type=action_type, params=params, reason=reason))

    return TeamleadDecision(actions=actions, summary=summary)
