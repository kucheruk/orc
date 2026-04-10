#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git helper utilities: status checks, command execution, integration classification."""

import subprocess
from pathlib import Path

from .logging import log_event

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
    lines = [ln.rstrip("\n") for ln in (porcelain or "").splitlines() if ln.strip()]
    tracked: list[str] = []
    untracked: list[str] = []
    for ln in lines:
        if ln.startswith("?? "):
            untracked.append(ln)
        else:
            tracked.append(ln)
    return tracked, untracked


def runtime_artifact_paths_from_porcelain_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    runtime: list[str] = []
    non_runtime: list[str] = []
    for ln in lines:
        path = ln[3:].strip() if len(ln) > 3 else ""
        if (
            path.startswith(".orc/")
            or path == ".cursor/orc-task-runtime.json"
            or path == ".cursor/orc-task.json"
            or path == ".cursor/orc-stop-request.json"
        ):
            runtime.append(ln)
        else:
            non_runtime.append(ln)
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


def classify_main_integration_error(error: str) -> str:
    text = (error or "").strip().lower()
    if not text:
        return "unknown"
    if "dirty before integration" in text:
        return "dirty_base_repo"
    if text.startswith("git status failed"):
        return "git_status_failed"
    if "main branch" in text and "not found" in text:
        return "main_branch_missing"
    if text.startswith("checkout"):
        return "checkout_failed"
    if "timeout" in text:
        return "git_timeout"
    if "cherry-pick" in text or "cherrypick" in text:
        return "cherry_pick_failed"
    return "unknown"
