#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git helper utilities: status checks, command execution, integration classification."""

import subprocess
from pathlib import Path

from ..infra.failure_reasons import IntegrationErrorKind
from ..log import log_event

GIT_COMMAND_TIMEOUT_SECONDS = 30.0


def run_git(
    workdir: str,
    args: list[str],
    *,
    timeout: float = GIT_COMMAND_TIMEOUT_SECONDS,
) -> tuple[bool, str, str, int]:
    """Run a git command and return (ok, stdout, stderr, returncode).

    This is the single entry point for synchronous git subprocess calls.
    """
    try:
        result = subprocess.run(
            args,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "", "timeout", 124
    except Exception as exc:
        return False, "", str(exc), 1
    return result.returncode == 0, result.stdout or "", result.stderr or "", int(result.returncode)


def git_run(workdir: str, log_path: Path, args: list[str], label: str) -> tuple[bool, str, str, int]:
    """Run a git command with structured logging on failure."""
    ok, stdout, stderr, rc = run_git(workdir, args)
    if not ok:
        if rc == 124:
            log_event(
                log_path, "ERROR", "git command timeout",
                label=label, timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS, args=" ".join(args),
            )
        else:
            log_event(
                log_path, "ERROR", "git command non-zero",
                label=label, returncode=rc, args=" ".join(args), stderr=stderr[:500],
            )
    return ok, stdout, stderr, rc


def git_status_porcelain(workdir: str, log_path: Path) -> tuple[bool, str]:
    ok, stdout, stderr, rc = git_run(workdir, log_path, ["git", "status", "--porcelain"], label="git_status")
    if not ok:
        return False, ""
    return True, stdout


def parse_git_porcelain(porcelain: str) -> tuple[list[str], list[str]]:
    tracked: list[str] = []
    untracked: list[str] = []
    for line in (porcelain or "").splitlines():
        if not line.strip():
            continue
        if line.startswith("??"):
            untracked.append(line[3:].strip())
        else:
            tracked.append(line[3:].strip())
    return tracked, untracked


_RUNTIME_ARTIFACT_PREFIXES = (".orc/", ".cursor/")


def is_runtime_artifact(path: str) -> bool:
    p = path.strip()
    if not p:
        return False
    if "__pycache__" in p or p.endswith(".pyc"):
        return True
    if p == "nohup.out":
        return True
    return any(p.startswith(pfx) or f"/{pfx}" in p for pfx in _RUNTIME_ARTIFACT_PREFIXES)


def runtime_artifact_paths_from_porcelain_lines(paths: list[str]) -> tuple[list[str], list[str]]:
    runtime: list[str] = []
    non_runtime: list[str] = []
    for p in paths:
        if is_runtime_artifact(p):
            runtime.append(p)
        else:
            non_runtime.append(p)
    return runtime, non_runtime


def attempt_autocommit_fallback(workdir: str, log_path: Path, task_id: str, task_text: str) -> bool:
    """
    Optional recovery step for commit phase when tracked changes remain.
    This path is strictly opt-in.
    """
    ok_add, _, _, _ = git_run(workdir, log_path, ["git", "add", "-A"], label="commit_fallback:add_all")
    if not ok_add:
        return False

    ok_quiet, _, _, rc = git_run(
        workdir,
        log_path,
        ["git", "diff", "--cached", "--quiet"],
        label="commit_fallback:cached_quiet",
    )
    if ok_quiet:
        return True
    if rc not in (1,):
        return False

    title = f"{task_id}: checkpoint"
    body = "Commit phase fallback: committed remaining changes left after commit phase."
    if task_text:
        body = f"{body}\n\nTask: {task_text}"
    ok_commit, _, _, _ = git_run(
        workdir,
        log_path,
        ["git", "commit", "-m", title, "-m", body],
        label="commit_fallback:commit",
    )
    return ok_commit


def has_commits_ahead_of_branch(workdir: str, branch: str, log_path: Path) -> bool:
    ok, stdout, stderr, _ = git_run(
        workdir,
        log_path,
        ["git", "rev-list", "--count", f"{branch}..HEAD"],
        label="integration:ahead_count",
    )
    if not ok:
        log_event(log_path, "ERROR", "failed to detect ahead commits", branch=branch, error=stderr[:200])
        return False
    try:
        return int((stdout or "0").strip() or "0") > 0
    except ValueError:
        log_event(log_path, "ERROR", "invalid ahead count output", branch=branch, output=stdout[:100])
        return False


_ERROR_PATTERNS: list[tuple[str, IntegrationErrorKind]] = [
    ("dirty before integration", IntegrationErrorKind.DIRTY_BASE_REPO),
    ("git status failed", IntegrationErrorKind.GIT_STATUS_FAILED),
    ("main branch", IntegrationErrorKind.MAIN_BRANCH_MISSING),  # also requires "not found"
    ("checkout", IntegrationErrorKind.CHECKOUT_FAILED),
    ("timeout", IntegrationErrorKind.GIT_TIMEOUT),
    ("cherry-pick", IntegrationErrorKind.CHERRY_PICK_FAILED),
    ("cherrypick", IntegrationErrorKind.CHERRY_PICK_FAILED),
]


def classify_main_integration_error(error: str) -> IntegrationErrorKind:
    text = (error or "").strip().lower()
    if not text:
        return IntegrationErrorKind.UNKNOWN
    for marker, kind in _ERROR_PATTERNS:
        if marker in text:
            # "main branch" requires "not found" as a second condition
            if kind == IntegrationErrorKind.MAIN_BRANCH_MISSING and "not found" not in text:
                continue
            return kind
    return IntegrationErrorKind.UNKNOWN


def git_diff_numstat(workdir: str, *, cached: bool = False, timeout: float = 10.0) -> str | None:
    """Run git diff --numstat and return stdout, or None on failure."""
    args = ["git", "diff", "--numstat"]
    if cached:
        args.append("--cached")
    ok, stdout, _, _ = run_git(workdir, args, timeout=timeout)
    if not ok:
        return None
    return stdout
