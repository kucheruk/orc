#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .logging import log_event
from .state_paths import worktrees_root

GIT_TIMEOUT_SECONDS = 30.0
INTEGRATION_SAFE_UNTRACKED_PREFIXES = (".orc/",)
INTEGRATION_SAFE_UNTRACKED_EXACT = {
    ".cursor/hooks.json",
    ".cursor/hooks/orc_before_submit.py",
    ".cursor/hooks/orc_hook_lib.py",
    ".cursor/hooks/orc_pre_tool_use.py",
    ".cursor/hooks/orc_stop.py",
    ".cursor/orc-stop-request.json",
    ".cursor/orc-task.json",
    ".cursor/orc-task-runtime.json",
}


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


@dataclass(frozen=True)
class IntegrationPreflightResult:
    ok: bool
    error: str = ""
    safe_tracked: tuple[str, ...] = ()
    safe_untracked: tuple[str, ...] = ()
    unsafe_tracked: tuple[str, ...] = ()
    unsafe_untracked: tuple[str, ...] = ()


def _safe_name(value: str, limit: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    if not cleaned:
        cleaned = "task"
    return cleaned[:limit]


def run_git(
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


def _parse_git_porcelain(porcelain: str) -> tuple[list[str], list[str]]:
    tracked: list[str] = []
    untracked: list[str] = []
    for raw_line in porcelain.splitlines():
        line = raw_line.rstrip("\n")
        if len(line) < 4:
            continue
        status = line[:2]
        path = line[3:].strip()
        if not path:
            continue
        if status == "??":
            untracked.append(path)
        else:
            tracked.append(path)
    return tracked, untracked


def _is_runtime_artifact_path(path: str) -> bool:
    normalized = path.strip()
    if not normalized:
        return False
    if normalized in INTEGRATION_SAFE_UNTRACKED_EXACT:
        return True
    return normalized.startswith(INTEGRATION_SAFE_UNTRACKED_PREFIXES)


def _is_integration_safe_untracked(path: str) -> bool:
    return _is_runtime_artifact_path(path)


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
    tracked, _ = _parse_git_porcelain(status_out)
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
    safe_tracked = [path for path in tracked if _is_integration_safe_untracked(path) or path in extra_safe]
    unsafe_tracked = [path for path in tracked if path not in safe_tracked]
    safe_untracked = [path for path in untracked if _is_integration_safe_untracked(path) or path in extra_safe]
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


def _is_empty_cherry_pick(stderr: str) -> bool:
    text = (stderr or "").lower()
    if "previous cherry-pick is now empty" in text:
        return True
    if "the previous cherry-pick is now empty" in text:
        return True
    if "cherry-pick is now empty" in text:
        return True
    if "nothing to commit" in text and "cherry-pick" in text:
        return True
    return False


def detect_base_branch(workdir: str) -> str:
    for candidate in ("main", "master"):
        ok, _, _, _ = run_git(workdir, ["git", "show-ref", "--verify", f"refs/heads/{candidate}"])
        if ok:
            return candidate
    ok, stdout, _, _ = run_git(workdir, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
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
    safe_task = _safe_name(task_id)
    branch_name = f"orc/{safe_task}"
    worktree_root = worktrees_root(base_workdir)
    worktree_root.mkdir(parents=True, exist_ok=True)
    worktree_path = worktree_root / safe_task

    if worktree_path.exists():
        # Reuse existing worktree — reset to main to pick up cherry-picked work
        ok_reset, _, stderr_reset, _ = run_git(
            str(worktree_path),
            ["git", "reset", "--hard", main_branch],
        )
        if ok_reset:
            log_event(log_path, "INFO", "task worktree reused",
                      task_id=task_id, worktree_path=str(worktree_path))
            return WorktreeSession(
                base_workdir=base_workdir,
                worktree_path=str(worktree_path),
                branch_name=branch_name,
                task_id=task_id,
            )
        # Reset failed — remove and recreate
        log_event(log_path, "WARN", "worktree reset failed, recreating",
                  task_id=task_id, error=stderr_reset.strip()[:200])
        run_git(base_workdir, ["git", "worktree", "remove", "--force", str(worktree_path)])
        run_git(base_workdir, ["git", "branch", "-D", branch_name])
        run_git(base_workdir, ["git", "worktree", "prune"])

    ok, _, stderr, _ = run_git(
        base_workdir,
        ["git", "worktree", "add", "-b", branch_name, str(worktree_path), main_branch],
    )
    if not ok:
        # Branch may already exist from a crashed run — try without -b
        ok2, _, stderr2, _ = run_git(
            base_workdir,
            ["git", "worktree", "add", str(worktree_path), branch_name],
        )
        if ok2:
            # Reset to main to be in sync
            ok_reset, _, stderr_r, _ = run_git(str(worktree_path), ["git", "reset", "--hard", main_branch])
            if not ok_reset:
                log_event(log_path, "WARN", "worktree reset to main failed",
                          task_id=task_id, error=stderr_r.strip()[:200])
        else:
            raise RuntimeError(f"failed to create worktree: {stderr.strip()} / {stderr2.strip()}")
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
    ok, _, stderr, _ = run_git(session.base_workdir, ["git", "worktree", "remove", session.worktree_path])
    if not ok:
        status_ok, status_out, status_err, _ = run_git(session.worktree_path, ["git", "status", "--porcelain"])
        if not status_ok:
            raise RuntimeError(f"failed to remove worktree: {stderr.strip()} (status check failed: {status_err.strip()})")
        dirty_paths = []
        for raw_line in status_out.splitlines():
            line = raw_line.rstrip("\n")
            if len(line) < 4:
                continue
            path = line[3:].strip()
            if path:
                dirty_paths.append(path)
        only_runtime_artifacts = bool(dirty_paths) and all(_is_runtime_artifact_path(path) for path in dirty_paths)
        if not only_runtime_artifacts:
            raise RuntimeError(f"failed to remove worktree: {stderr.strip()}")
        log_event(
            log_path,
            "WARN",
            "worktree cleanup fallback: force remove due to runtime artifacts",
            task_id=session.task_id,
            worktree_path=session.worktree_path,
            dirty_paths=dirty_paths[:20],
        )
        ok_force, _, stderr_force, _ = run_git(
            session.base_workdir,
            ["git", "worktree", "remove", "--force", session.worktree_path],
        )
        if not ok_force:
            raise RuntimeError(f"failed to force remove worktree: {stderr_force.strip()}")
    run_git(session.base_workdir, ["git", "worktree", "prune"])
    # Delete the task branch after worktree removal (it's been cherry-picked to main)
    if session.branch_name:
        branch_ok, _, branch_err, _ = run_git(
            session.base_workdir,
            ["git", "branch", "-D", session.branch_name],
        )
        if branch_ok:
            log_event(log_path, "INFO", "task branch deleted",
                      task_id=session.task_id, branch=session.branch_name)
        else:
            log_event(log_path, "WARN", "failed to delete task branch",
                      task_id=session.task_id, branch=session.branch_name,
                      error=branch_err.strip()[:200])
    log_event(
        log_path,
        "INFO",
        "task worktree removed",
        task_id=session.task_id,
        worktree_path=session.worktree_path,
    )


def get_head_commit(workdir: str) -> str:
    ok, stdout, stderr, _ = run_git(workdir, ["git", "rev-parse", "HEAD"])
    if not ok:
        raise RuntimeError(f"failed to get HEAD commit: {stderr.strip()}")
    return stdout.strip()


def _is_commit_in_branch(workdir: str, commit_sha: str, branch: str) -> bool:
    ok, _, _, rc = run_git(workdir, ["git", "merge-base", "--is-ancestor", commit_sha, branch])
    if ok:
        return True
    return False


def _cherry_pick_commit(workdir: str, commit_sha: str) -> tuple[bool, bool, str]:
    ok, _, stderr, _ = run_git(workdir, ["git", "cherry-pick", "-x", commit_sha])
    if ok:
        return True, False, ""
    if _is_empty_cherry_pick(stderr):
        return False, False, stderr.strip()
    ok_conflicts, conflict_files, _, _ = run_git(workdir, ["git", "diff", "--name-only", "--diff-filter=U"])
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
    skip_preflight: bool = False,
) -> IntegrationResult:
    if not skip_preflight:
        preflight = preflight_main_integration(base_workdir=base_workdir, main_branch=main_branch)
        if not preflight.ok:
            return IntegrationResult(ok=False, conflict=False, error=preflight.error)
        if preflight.safe_tracked or preflight.safe_untracked:
            log_event(
                log_path,
                "WARN",
                "ignoring runtime artifacts before integration",
                task_id=task_id,
                tracked_runtime=list(preflight.safe_tracked[:20]),
                untracked_runtime=list(preflight.safe_untracked[:20]),
            )

    ok_checkout, _, stderr_checkout, _ = run_git(base_workdir, ["git", "checkout", main_branch])
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
    if _is_empty_cherry_pick(pick_error):
        log_event(
            log_path,
            "WARN",
            "cherry-pick produced empty change; treating as already integrated",
            task_id=task_id,
            commit_sha=commit_sha,
            branch=main_branch,
        )
        return IntegrationResult(ok=True, conflict=False, already_integrated=True)
    return IntegrationResult(ok=False, conflict=False, error=pick_error)
