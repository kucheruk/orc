#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban role registry: single source of truth for role names and prompt file mappings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ── Worker role constants ──────────────────────────────────────────

ROLE_PRODUCT = "product"
ROLE_ARCHITECT = "architect"
ROLE_CODER = "coder"
ROLE_REVIEWER = "reviewer"
ROLE_TESTER = "tester"
ROLE_INTEGRATOR = "integrator"

# ── Teamlead role constants ───────────────────────────────────────

ROLE_TEAMLEAD = "teamlead"
ROLE_TEAMLEAD_TRIAGE = "teamlead_triage"

# ── Registry ──────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parents[2]
_PROMPTS_DIR = _BASE_DIR / "prompts"

_ROLE_PROMPT_FILES: dict[str, str] = {
    ROLE_PRODUCT: "kanban_product.txt",
    ROLE_ARCHITECT: "kanban_architect.txt",
    ROLE_CODER: "kanban_coder.txt",
    ROLE_REVIEWER: "kanban_reviewer.txt",
    ROLE_TESTER: "kanban_tester.txt",
    ROLE_INTEGRATOR: "kanban_integrator.txt",
    ROLE_TEAMLEAD: "kanban_teamlead.txt",
    ROLE_TEAMLEAD_TRIAGE: "kanban_teamlead_triage.txt",
}

_template_cache: dict[str, str] = {}


def register_role(name: str, prompt_file: str) -> None:
    """Register a new kanban role with its prompt template filename."""
    _ROLE_PROMPT_FILES[name] = prompt_file
    _template_cache.pop(name, None)


def load_role_template(role: str) -> str:
    """Load and cache the prompt template for a role."""
    if role in _template_cache:
        return _template_cache[role]
    filename = _ROLE_PROMPT_FILES.get(role)
    if not filename:
        raise ValueError(f"Unknown kanban role: {role!r}. "
                         f"Known roles: {', '.join(sorted(_ROLE_PROMPT_FILES))}")
    path = _PROMPTS_DIR / filename
    template = path.read_text(encoding="utf-8")
    _template_cache[role] = template
    return template


def clear_template_cache() -> None:
    """Clear the template cache (useful for testing)."""
    _template_cache.clear()


def known_roles() -> list[str]:
    """Return all registered role names."""
    return sorted(_ROLE_PROMPT_FILES.keys())
