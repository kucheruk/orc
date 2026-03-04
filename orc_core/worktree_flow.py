#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .logging import log_event

GIT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class WorktreeSession:
    base_workdir: str
    worktree_path: str
    branch_name: str
    task_id: str


@dataclass(frozen=True)
class IntegrationResult:
    ok: bool
    conflict: bool
    already_integrated: bool = False
    error: str = ""


def _safe_name(value: str, limit: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    if not cleaned:
        cleaned = "task"
    return cleaned[:limit]


def _git(
    workdir: str,
    args: list[str],
) -> tuple[bool, str, str, int]:
    try:
        result = subprocess.run(
            args,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "", "timeout", 124
    except Exception as exc:  # pragma: no cover - defensive
        return False, "", str(exc), 1
    return result.returncode == 0, result.stdout or "", result.stderr or "", int(result.returncode)


def detect_base_branch(workdir: str) -> str:
    for candidate in ("main", "master"):
        ok, _, _, _ = _git(workdir, ["git", "show-ref", "--verify", f"refs/heads/{candidate}"])
        if ok:
            return candidate
    ok, stdout, _, _ = _git(workdir, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
    current = stdout.strip() if ok else ""
    if current and current != "HEAD":
        return current
    return "main"


def create_task_worktree(
    *,
    base_workdir: str,
    task_id: str,
    log_path: Path,
    main_branch: str = "main",
) -> WorktreeSession:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_task = _safe_name(task_id)
    branch_name = f"orc/{safe_task}-{stamp}"
    worktree_root = Path(base_workdir) / ".orc" / "worktrees"
    worktree_root.mkdir(parents=True, exist_ok=True)
    worktree_path = worktree_root / f"{safe_task}-{stamp}"
    ok, _, stderr, _ = _git(
        base_workdir,
        ["git", "worktree", "add", "-b", branch_name, str(worktree_path), main_branch],
    )
    if not ok:
        raise RuntimeError(f"failed to create worktree: {stderr.strip()}")
    log_event(
        log_path,
        "INFO",
        "task worktree created",
        task_id=task_id,
        worktree_path=str(worktree_path),
        branch_name=branch_name,
    )
    return WorktreeSession(
        base_workdir=base_workdir,
        worktree_path=str(worktree_path),
        branch_name=branch_name,
        task_id=task_id,
    )


def cleanup_task_worktree(session: WorktreeSession, log_path: Path) -> None:
    ok, _, stderr, _ = _git(session.base_workdir, ["git", "worktree", "remove", session.worktree_path])
    if not ok:
        raise RuntimeError(f"failed to remove worktree: {stderr.strip()}")
    _git(session.base_workdir, ["git", "worktree", "prune"])
    log_event(
        log_path,
        "INFO",
        "task worktree removed",
        task_id=session.task_id,
        worktree_path=session.worktree_path,
    )


def get_head_commit(workdir: str) -> str:
    ok, stdout, stderr, _ = _git(workdir, ["git", "rev-parse", "HEAD"])
    if not ok:
        raise RuntimeError(f"failed to get HEAD commit: {stderr.strip()}")
    return stdout.strip()


def _is_commit_in_branch(workdir: str, commit_sha: str, branch: str) -> bool:
    ok, _, _, rc = _git(workdir, ["git", "merge-base", "--is-ancestor", commit_sha, branch])
    if ok:
        return True
    return rc == 1 and False


def _cherry_pick_commit(workdir: str, commit_sha: str) -> tuple[bool, bool, str]:
    ok, _, stderr, _ = _git(workdir, ["git", "cherry-pick", "-x", commit_sha])
    if ok:
        return True, False, ""
    ok_conflicts, conflict_files, _, _ = _git(workdir, ["git", "diff", "--name-only", "--diff-filter=U"])
    if ok_conflicts and bool(conflict_files.strip()):
        return False, True, stderr.strip()
    lowered = stderr.lower()
    if "conflict" in lowered:
        return False, True, stderr.strip()
    return False, False, stderr.strip()


def integrate_commit_into_main(
    *,
    base_workdir: str,
    commit_sha: str,
    task_id: str,
    log_path: Path,
    main_branch: str = "main",
) -> IntegrationResult:
    ok_status, status_out, status_err, _ = _git(base_workdir, ["git", "status", "--porcelain"])
    if not ok_status:
        return IntegrationResult(ok=False, conflict=False, error=f"git status failed: {status_err.strip()}")
    if status_out.strip():
        return IntegrationResult(ok=False, conflict=False, error="base repository is dirty before integration")

    ok_checkout, _, stderr_checkout, _ = _git(base_workdir, ["git", "checkout", main_branch])
    if not ok_checkout:
        return IntegrationResult(ok=False, conflict=False, error=f"checkout {main_branch} failed: {stderr_checkout.strip()}")

    if _is_commit_in_branch(base_workdir, commit_sha, main_branch):
        log_event(
            log_path,
            "INFO",
            "task commit already integrated in main",
            task_id=task_id,
            commit_sha=commit_sha,
            branch=main_branch,
        )
        return IntegrationResult(ok=True, conflict=False, already_integrated=True)

    ok_pick, has_conflict, pick_error = _cherry_pick_commit(base_workdir, commit_sha)
    if ok_pick:
        log_event(
            log_path,
            "INFO",
            "task commit integrated in main",
            task_id=task_id,
            commit_sha=commit_sha,
            branch=main_branch,
        )
        return IntegrationResult(ok=True, conflict=False)
    if has_conflict:
        log_event(
            log_path,
            "WARN",
            "cherry-pick conflict while integrating task commit",
            task_id=task_id,
            commit_sha=commit_sha,
            branch=main_branch,
            error=pick_error[:500],
        )
        return IntegrationResult(ok=False, conflict=True, error=pick_error)
    return IntegrationResult(ok=False, conflict=False, error=pick_error)
