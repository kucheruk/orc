#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapters wiring git/ to tasks.ports (GitDiffProbe, MainIntegrationPreflight)."""
from __future__ import annotations

from typing import Optional

from ..tasks.ports import PreflightResult
from .git_helpers import classify_main_integration_error, git_diff_numstat
from .worktree_flow import preflight_main_integration


class SubprocessGitDiffProbe:
    """GitDiffProbe backed by subprocess git."""

    def get_numstat(self, workdir: str, *, cached: bool = False, timeout: float = 10.0) -> Optional[str]:
        return git_diff_numstat(workdir, cached=cached, timeout=timeout)


class SubprocessMainIntegrationPreflight:
    """MainIntegrationPreflight backed by subprocess git."""

    def run(
        self,
        *,
        base_workdir: str,
        main_branch: str,
        extra_safe_paths: frozenset[str] = frozenset(),
    ) -> PreflightResult:
        result = preflight_main_integration(
            base_workdir=base_workdir,
            main_branch=main_branch,
            extra_safe_paths=extra_safe_paths,
        )
        return PreflightResult(
            ok=result.ok,
            error=result.error,
            safe_tracked=tuple(getattr(result, "safe_tracked", ()) or ()),
            safe_untracked=tuple(getattr(result, "safe_untracked", ()) or ()),
            unsafe_tracked=tuple(getattr(result, "unsafe_tracked", ()) or ()),
            unsafe_untracked=tuple(getattr(result, "unsafe_untracked", ()) or ()),
        )

    def classify_error(self, error: str) -> str:
        return classify_main_integration_error(error)


DEFAULT_GIT_DIFF_PROBE = SubprocessGitDiffProbe()
DEFAULT_MAIN_INTEGRATION_PREFLIGHT = SubprocessMainIntegrationPreflight()
