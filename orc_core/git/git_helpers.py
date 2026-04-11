#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git helper utilities: status checks, command execution, integration classification."""

import subprocess
from pathlib import Path

from ..infra.failure_reasons import IntegrationErrorKind
from ..infra.logging import log_event

GIT_COMMAND_TIMEOUT_SECONDS = 20.0


def git_status_porcelain(workdir: str, log_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log_event(log_path, "ERROR", "git status timeout", timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS)
        return False, ""
    except Exception as exc:
        log_event(log_path, "ERROR", "git status failed", error=str(exc))
        return False, ""
    if result.returncode != 0:
        log_event(
            log_path,
            "ERROR",
            "git status non-zero",
            returncode=result.returncode,
            stderr=(result.stderr or "")[:500],
        )
        return False, ""
    return True, result.stdout or ""


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


def git_run(workdir: str, log_path: Path, args: list[str], label: str) -> tuple[bool, str, str, int]:
    try:
        result = subprocess.run(
            args,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log_event(
            log_path,
            "ERROR",
            "git command timeout",
            label=label,
            timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS,
            args=" ".join(args),
        )
        return False, "", "timeout", 124
    except Exception as exc:
        log_event(log_path, "ERROR", "git command failed", label=label, error=str(exc), args=" ".join(args))
        return False, "", str(exc), 1
    ok = result.returncode == 0
    if not ok:
        log_event(
            log_path,
            "ERROR",
            "git command non-zero",
            label=label,
            returncode=result.returncode,
            args=" ".join(args),
            stderr=(result.stderr or "")[:500],
        )
    return ok, result.stdout or "", result.stderr or "", int(result.returncode)


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


def classify_main_integration_error(error: str) -> IntegrationErrorKind:
    text = (error or "").strip().lower()
    if not text:
        return IntegrationErrorKind.UNKNOWN
    if "dirty before integration" in text:
        return IntegrationErrorKind.DIRTY_BASE_REPO
    if text.startswith("git status failed"):
        return IntegrationErrorKind.GIT_STATUS_FAILED
    if "main branch" in text and "not found" in text:
        return IntegrationErrorKind.MAIN_BRANCH_MISSING
    if text.startswith("checkout"):
        return IntegrationErrorKind.CHECKOUT_FAILED
    if "timeout" in text:
        return IntegrationErrorKind.GIT_TIMEOUT
    if "cherry-pick" in text or "cherrypick" in text:
        return IntegrationErrorKind.CHERRY_PICK_FAILED
    return IntegrationErrorKind.UNKNOWN


def git_diff_numstat(workdir: str, *, cached: bool = False, timeout: float = 10.0) -> str | None:
    """Run git diff --numstat and return stdout, or None on failure."""
    args = ["git", "diff", "--numstat"]
    if cached:
        args.append("--cached")
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
    except (subprocess.TimeoutExpired, Exception):
        return None
    if result.returncode != 0:
        return None
    return result.stdout
