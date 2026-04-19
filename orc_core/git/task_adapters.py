#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapters wiring git/ to the ports declared in tasks.ports.

Provides concrete, subprocess-backed implementations of:
- GitDiffProbe (`SubprocessGitDiffProbe`)
- MainIntegrationPreflight (`SubprocessMainIntegrationPreflight`)
- GitIntegrationPort (`SubprocessGitIntegration`) — bundles every
  git-touching helper that `tasks/` and `agents/runners/` need, so
  those layers no longer import `git.git_helpers` / `git.worktree_flow`
  directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..tasks.ports import GitIntegrationPort, IntegrationOutcome, PreflightResult
from .git_helpers import (
    attempt_autocommit_fallback,
    board_commit_message,
    classify_main_integration_error,
    git_diff_numstat,
    git_run,
    git_status_porcelain,
    has_commits_ahead_of_branch,
    is_runtime_artifact,
    parse_git_porcelain,
    run_git,
    runtime_artifact_paths_from_porcelain_lines,
    sync_commit_message,
)
from .worktree_flow import (
    abort_merge,
    merge_task_branch_into_main,
    preflight_main_integration,
    task_branch_name,
)


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


class SubprocessGitIntegration:
    """Concrete `GitIntegrationPort` backed by the subprocess git helpers."""

    # ── shell primitives ──────────────────────────────────────────
    def run(self, workdir: str, args: list[str], *, timeout: float = 30.0) -> tuple[bool, str, str, int]:
        return run_git(workdir, args, timeout=timeout)

    def run_with_log(
        self, workdir: str, log_path: Path, args: list[str], *, label: str
    ) -> tuple[bool, str, str, int]:
        return git_run(workdir, log_path, args, label)

    # ── porcelain helpers ─────────────────────────────────────────
    def status_porcelain(self, workdir: str, log_path: Path) -> tuple[bool, str]:
        return git_status_porcelain(workdir, log_path)

    def parse_porcelain(self, porcelain: str) -> tuple[list[str], list[str]]:
        return parse_git_porcelain(porcelain)

    def is_runtime_artifact(self, path: str) -> bool:
        return is_runtime_artifact(path)

    def split_runtime_artifacts(self, paths: list[str]) -> tuple[list[str], list[str]]:
        return runtime_artifact_paths_from_porcelain_lines(paths)

    # ── autocommit ────────────────────────────────────────────────
    def attempt_autocommit_fallback(
        self, workdir: str, log_path: Path, task_id: str, task_text: str
    ) -> bool:
        return attempt_autocommit_fallback(workdir, log_path, task_id, task_text)

    # ── naming / messages ─────────────────────────────────────────
    def task_branch_name(self, task_id: str) -> str:
        return task_branch_name(task_id)

    def board_commit_message(self) -> str:
        return board_commit_message()

    def sync_commit_message(self) -> str:
        return sync_commit_message()

    # ── integration ───────────────────────────────────────────────
    def has_commits_ahead_of_branch(self, workdir: str, branch: str, log_path: Path) -> bool:
        return has_commits_ahead_of_branch(workdir, branch, log_path)

    def merge_task_branch_into_main(
        self,
        *,
        base_workdir: str,
        branch_name: str,
        task_id: str,
        task_title: str,
        log_path: Path,
        main_branch: str,
        skip_preflight: bool = False,
    ) -> IntegrationOutcome:
        result = merge_task_branch_into_main(
            base_workdir=base_workdir,
            branch_name=branch_name,
            task_id=task_id,
            task_title=task_title,
            log_path=log_path,
            main_branch=main_branch,
            skip_preflight=skip_preflight,
        )
        return IntegrationOutcome(
            ok=result.ok,
            conflict=result.conflict,
            already_integrated=result.already_integrated,
            error=result.error,
        )

    def abort_merge(self, workdir: str) -> bool:
        return abort_merge(workdir)

    def classify_main_integration_error(self, error: str) -> str:
        return classify_main_integration_error(error)


DEFAULT_GIT_DIFF_PROBE = SubprocessGitDiffProbe()
DEFAULT_MAIN_INTEGRATION_PREFLIGHT = SubprocessMainIntegrationPreflight()
DEFAULT_GIT_INTEGRATION: GitIntegrationPort = SubprocessGitIntegration()
