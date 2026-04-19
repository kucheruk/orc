#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Branch naming and ref resolution helpers."""

from __future__ import annotations

import re

from .git_helpers import is_runtime_artifact, run_git


DEFAULT_MAIN_BRANCH = "main"

_BRANCH_PREFIX = "orc/"


def _safe_name(value: str, limit: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    if not cleaned:
        cleaned = "task"
    return cleaned[:limit]


def task_branch_name(task_id: str) -> str:
    """Canonical branch name for a task — single source of truth."""
    return f"{_BRANCH_PREFIX}{_safe_name(task_id)}"


def detect_base_branch(workdir: str) -> str:
    for candidate in ("main", "master"):
        ok, _, _, _ = run_git(workdir, ["git", "show-ref", "--verify", f"refs/heads/{candidate}"])
        if ok:
            return candidate
    ok, stdout, _, _ = run_git(workdir, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
    current = stdout.strip() if ok else ""
    if current and current != "HEAD":
        return current
    return DEFAULT_MAIN_BRANCH


def get_head_commit(workdir: str) -> str:
    ok, stdout, stderr, _ = run_git(workdir, ["git", "rev-parse", "HEAD"])
    if not ok:
        raise RuntimeError(f"failed to get HEAD commit: {stderr.strip()}")
    return stdout.strip()


def _list_commit_files(workdir: str, commit_sha: str) -> list[str]:
    ok, stdout, _, _ = run_git(workdir, ["git", "show", "--pretty=format:", "--name-only", commit_sha])
    if not ok:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def _is_orchestration_only_path(path: str) -> bool:
    normalized = (path or "").strip()
    return normalized.startswith("tasks/") or is_runtime_artifact(normalized)


def resolve_integration_commit(workdir: str, main_branch: str) -> str:
    """Resolve the commit that should be integrated into main.

    Prefer the latest non-merge commit ahead of main. This avoids trying to
    cherry-pick synthetic merge commits created by "git merge <main>" inside
    task worktrees.
    """
    ok, stdout, stderr, _ = run_git(
        workdir,
        ["git", "rev-list", "--no-merges", f"{main_branch}..HEAD"],
    )
    if not ok:
        raise RuntimeError(f"failed to resolve non-merge integration commit: {stderr.strip()}")
    commits = [line.strip() for line in stdout.splitlines() if line.strip()]
    if commits:
        for commit_sha in commits:
            changed_files = _list_commit_files(workdir, commit_sha)
            if not changed_files:
                continue
            if all(_is_orchestration_only_path(path) for path in changed_files):
                continue
            return commit_sha
        raise RuntimeError("no deliverable commit ahead of main (only tasks/runtime changes)")
    return get_head_commit(workdir)
