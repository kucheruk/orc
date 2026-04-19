#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban role registry: single source of truth for role names, prompt
files, and capability flags (`requires_worktree`, `is_delivery`)."""

from __future__ import annotations

from dataclasses import dataclass, replace
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


# ── Role profile & registry ───────────────────────────────────────


@dataclass(frozen=True)
class KanbanRoleProfile:
    """Capabilities of a kanban role.

    - `requires_worktree`: the role needs an isolated git worktree to run
      (any role that touches source code).
    - `is_delivery`: the role is expected to produce code commits for a
      card (CODER/REVIEWER/TESTER); consumed by post-run guards that
      reject empty deliveries.
    """

    name: str
    prompt_file: str
    requires_worktree: bool = False
    is_delivery: bool = False


_DEFAULT_PROFILES: tuple[KanbanRoleProfile, ...] = (
    KanbanRoleProfile(ROLE_PRODUCT, "kanban_product.txt"),
    KanbanRoleProfile(ROLE_ARCHITECT, "kanban_architect.txt"),
    KanbanRoleProfile(ROLE_CODER, "kanban_coder.txt", requires_worktree=True, is_delivery=True),
    KanbanRoleProfile(ROLE_REVIEWER, "kanban_reviewer.txt", requires_worktree=True, is_delivery=True),
    KanbanRoleProfile(ROLE_TESTER, "kanban_tester.txt", requires_worktree=True, is_delivery=True),
    KanbanRoleProfile(ROLE_INTEGRATOR, "kanban_integrator.txt", requires_worktree=True, is_delivery=False),
    KanbanRoleProfile(ROLE_TEAMLEAD, "kanban_teamlead.txt"),
    KanbanRoleProfile(ROLE_TEAMLEAD_TRIAGE, "kanban_teamlead_triage.txt"),
)


_PROFILES: dict[str, KanbanRoleProfile] = {p.name: p for p in _DEFAULT_PROFILES}


def register_role_profile(profile: KanbanRoleProfile) -> None:
    """Register or replace a full role profile."""
    _PROFILES[profile.name] = profile


def register_role(name: str, prompt_file: str) -> None:
    """Legacy registration. Creates a default (non-worktree, non-delivery) profile.

    New code should use `register_role_profile` to set capabilities.
    """
    existing = _PROFILES.get(name)
    if existing is None:
        _PROFILES[name] = KanbanRoleProfile(name=name, prompt_file=prompt_file)
    else:
        _PROFILES[name] = replace(existing, prompt_file=prompt_file)


def known_roles() -> list[str]:
    """Return all registered role names."""
    return sorted(_PROFILES.keys())


def role_profile(role: str) -> KanbanRoleProfile:
    """Return the profile for a role, raising ValueError on unknown roles."""
    profile = _PROFILES.get(role)
    if profile is None:
        raise ValueError(
            f"Unknown kanban role: {role!r}. "
            f"Known roles: {', '.join(sorted(_PROFILES))}"
        )
    return profile


def role_prompt_filename(role: str) -> str:
    """Return the prompt filename for a role, raising on unknown roles."""
    return role_profile(role).prompt_file


def is_delivery_role(role: str) -> bool:
    """True for roles expected to produce code commits (CODER/REVIEWER/TESTER)."""
    profile = _PROFILES.get(role)
    return bool(profile and profile.is_delivery)


def requires_worktree(role: str) -> bool:
    """True for roles that need an isolated git worktree to operate."""
    profile = _PROFILES.get(role)
    return bool(profile and profile.requires_worktree)


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
