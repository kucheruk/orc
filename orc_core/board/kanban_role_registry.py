#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban role registry: single source of truth for role names and prompt file mappings."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

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


def register_role(name: str, prompt_file: str) -> None:
    """Register a new kanban role with its prompt template filename."""
    _ROLE_PROMPT_FILES[name] = prompt_file


def known_roles() -> list[str]:
    """Return all registered role names."""
    return sorted(_ROLE_PROMPT_FILES.keys())


def role_prompt_filename(role: str) -> str:
    """Return the prompt filename for a role, raising on unknown roles."""
    filename = _ROLE_PROMPT_FILES.get(role)
    if not filename:
        raise ValueError(
            f"Unknown kanban role: {role!r}. "
            f"Known roles: {', '.join(sorted(_ROLE_PROMPT_FILES))}"
        )
    return filename


# ── Template loader port & default implementation ─────────────────


class TemplateLoader(Protocol):
    """Port for loading role prompt templates."""

    def load(self, role: str) -> str: ...


class FileTemplateLoader:
    """Load prompt templates from a directory on disk, caching per-role."""

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._cache: dict[str, str] = {}

    def load(self, role: str) -> str:
        cached = self._cache.get(role)
        if cached is not None:
            return cached
        filename = role_prompt_filename(role)
        template = (self._dir / filename).read_text(encoding="utf-8")
        self._cache[role] = template
        return template

    def clear_cache(self) -> None:
        self._cache.clear()


def _default_prompts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


def default_template_loader() -> FileTemplateLoader:
    """Factory — build a FileTemplateLoader rooted at the bundled prompts/ dir."""
    return FileTemplateLoader(_default_prompts_dir())
