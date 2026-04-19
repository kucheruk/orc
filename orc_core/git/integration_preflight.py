#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main-branch integration preflight checks."""

from __future__ import annotations

from .git_dto import IntegrationPreflightResult
from .git_helpers import is_runtime_artifact, parse_git_porcelain, run_git


def _list_untracked_files(workdir: str) -> tuple[bool, list[str], str]:
    ok, stdout, stderr, _ = run_git(workdir, ["git", "ls-files", "--others", "--exclude-standard"])
    if not ok:
        return False, [], f"git ls-files failed: {stderr.strip()}"
    untracked = [line.strip() for line in stdout.splitlines() if line.strip()]
    return True, untracked, ""


def _collect_integration_repo_state(workdir: str) -> tuple[bool, list[str], list[str], str]:
    ok_status, status_out, status_err, _ = run_git(workdir, ["git", "status", "--porcelain", "--untracked-files=no"])
    if not ok_status:
        return False, [], [], f"git status failed: {status_err.strip()}"
    tracked, _ = parse_git_porcelain(status_out)
    ok_untracked, untracked, untracked_err = _list_untracked_files(workdir)
    if not ok_untracked:
        return False, [], [], untracked_err
    return True, tracked, untracked, ""


def _summarize_dirty_paths(tracked: list[str], untracked: list[str], limit: int = 10) -> str:
    parts: list[str] = []
    if tracked:
        parts.extend(f"tracked:{path}" for path in tracked)
    if untracked:
        parts.extend(f"untracked:{path}" for path in untracked)
    if not parts:
        return ""
    sliced = parts[:limit]
    if len(parts) > limit:
        sliced.append(f"... (+{len(parts) - limit} more)")
    return ", ".join(sliced)


def _evaluate_integration_repo_safety(
    tracked: list[str],
    untracked: list[str],
    extra_safe: frozenset[str] = frozenset(),
) -> IntegrationPreflightResult:
    safe_tracked = [path for path in tracked if is_runtime_artifact(path) or path in extra_safe]
    unsafe_tracked = [path for path in tracked if path not in safe_tracked]
    safe_untracked = [path for path in untracked if is_runtime_artifact(path) or path in extra_safe]
    unsafe_untracked = [path for path in untracked if path not in safe_untracked]
    if unsafe_tracked or unsafe_untracked:
        error_summary = _summarize_dirty_paths(unsafe_tracked, unsafe_untracked)
        error = "base repository is dirty before integration"
        if error_summary:
            error = f"{error}: {error_summary}"
        return IntegrationPreflightResult(
            ok=False,
            error=error,
            safe_tracked=tuple(safe_tracked),
            safe_untracked=tuple(safe_untracked),
            unsafe_tracked=tuple(unsafe_tracked),
            unsafe_untracked=tuple(unsafe_untracked),
        )
    return IntegrationPreflightResult(
        ok=True,
        safe_tracked=tuple(safe_tracked),
        safe_untracked=tuple(safe_untracked),
    )


def preflight_main_integration(
    *,
    base_workdir: str,
    main_branch: str,
    extra_safe_paths: frozenset[str] = frozenset(),
) -> IntegrationPreflightResult:
    ok_state, tracked, untracked, state_error = _collect_integration_repo_state(base_workdir)
    if not ok_state:
        return IntegrationPreflightResult(ok=False, error=state_error)
    safety = _evaluate_integration_repo_safety(tracked, untracked, extra_safe_paths)
    if not safety.ok:
        return safety
    ok_branch, _, stderr_branch, _ = run_git(base_workdir, ["git", "show-ref", "--verify", f"refs/heads/{main_branch}"])
    if not ok_branch:
        return IntegrationPreflightResult(
            ok=False,
            error=f"main branch '{main_branch}' not found: {stderr_branch.strip()}",
            safe_tracked=safety.safe_tracked,
            safe_untracked=safety.safe_untracked,
        )
    return safety
