#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git helper utilities: status checks, command execution, integration classification."""

from pathlib import Path

from ..errors.failure_reasons import IntegrationErrorKind
from ..log import log_event
from .subprocess_git import GIT_COMMAND_TIMEOUT_SECONDS, SubprocessGitRunner

_default_runner = SubprocessGitRunner()


def run_git(
    workdir: str,
    args: list[str],
    *,
    timeout: float = GIT_COMMAND_TIMEOUT_SECONDS,
) -> tuple[bool, str, str, int]:
    """Run a git command via the default SubprocessGitRunner.

    Module-level convenience — class-based callers should depend on the
    GitRunner port instead and receive a runner via DI.
    """
    return _default_runner.run(workdir, args, timeout=timeout)


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

    title = f"chore({task_id}): checkpoint commit"
    body = "Autocommit fallback: committed remaining changes after agent completion."
    if task_text:
        body = f"{body}\n\nRefs: {task_id}"
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


def has_code_changes_ahead(workdir: str, branch: str, log_path: Path) -> bool:
    """Check whether the worktree branch has source-code changes vs *branch*.

    Returns True when either:
    - committed changes exist outside ``tasks/`` (vs branch), OR
    - uncommitted/untracked source files exist outside ``tasks/``.

    This prevents the delivery gate from passing on card-only commits
    and also catches agents that write code but fail to commit.
    """
    # 1. Check committed changes
    ok, stdout, stderr, _ = git_run(
        workdir,
        log_path,
        ["git", "diff", "--name-only", f"{branch}..HEAD", "--", ".", ":!tasks/"],
        label="integration:code_changes",
    )
    if not ok:
        log_event(log_path, "ERROR", "failed to detect code changes",
                  branch=branch, error=stderr[:200])
        return False
    changed = [line for line in (stdout or "").splitlines() if line.strip()]
    if changed:
        log_event(log_path, "INFO", "code changes detected (committed)",
                  branch=branch, count=len(changed), sample=changed[:5])
        return True

    # 2. Check uncommitted/untracked changes outside tasks/
    ok2, porcelain, _, _ = git_run(
        workdir, log_path, ["git", "status", "--porcelain"], label="integration:uncommitted_check",
    )
    if ok2 and porcelain:
        tracked, untracked = parse_git_porcelain(porcelain)
        code_dirty = [p for p in tracked + untracked if not p.startswith("tasks/")]
        if code_dirty:
            log_event(log_path, "INFO", "code changes detected (uncommitted)",
                      branch=branch, count=len(code_dirty), sample=code_dirty[:5])
            return True

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
