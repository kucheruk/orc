#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Domain types for git operations (worktrees, integration results).

These are domain value objects — they belong in the models layer,
not in git infrastructure, so that inner layers (models, use_cases)
can reference them without depending on git/.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorktreeSession:
    base_workdir: str
    worktree_path: str
    branch_name: str
    task_id: str
    reused: bool = False


@dataclass(frozen=True)
class IntegrationResult:
    ok: bool
    conflict: bool
    already_integrated: bool = False
    error: str = ""


@dataclass(frozen=True)
class IntegrationPreflightResult:
    ok: bool
    error: str = ""
    safe_tracked: tuple[str, ...] = ()
    safe_untracked: tuple[str, ...] = ()
    unsafe_tracked: tuple[str, ...] = ()
    unsafe_untracked: tuple[str, ...] = ()
