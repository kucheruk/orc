#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from .git_helpers import is_runtime_artifact, parse_git_porcelain as _parse_git_porcelain, run_git
from ..log import log_event
from ..infra.io.state_paths import worktrees_root
from .git_dto import IntegrationPreflightResult, IntegrationResult, WorktreeSession


def _safe_name(value: str, limit: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    if not cleaned:
        cleaned = "task"
    return cleaned[:limit]


DEFAULT_MAIN_BRANCH = "main"

_BRANCH_PREFIX = "orc/"


def task_branch_name(task_id: str) -> str:
    """Canonical branch name for a task — single source of truth."""
    return f"{_BRANCH_PREFIX}{_safe_name(task_id)}"



_is_runtime_artifact_path = is_runtime_artifact
_is_integration_safe_untracked = is_runtime_artifact


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
    return DEFAULT_MAIN_BRANCH


def create_task_worktree(
    *,
    base_workdir: str,
    task_id: str,
    log_path: Path,
    main_branch: str = DEFAULT_MAIN_BRANCH,
) -> WorktreeSession:
    safe_task = _safe_name(task_id)
    branch_name = task_branch_name(task_id)
    worktree_root = worktrees_root(base_workdir)
    worktree_root.mkdir(parents=True, exist_ok=True)
    worktree_path = worktree_root / safe_task

    if worktree_path.exists():
        # Verify the existing worktree belongs to the same card ID.
        # _safe_name can collapse different IDs (e.g., "X-1!" and "X-1?" both → "X-1").
        owner_file = worktree_path / ".orc-card-id"
        if owner_file.exists():
            owner_id = owner_file.read_text(encoding="utf-8").strip()
            if owner_id and owner_id != task_id:
                log_event(log_path, "ERROR", "worktree collision detected",
                          task_id=task_id, owner_id=owner_id,
                          safe_name=safe_task, worktree_path=str(worktree_path))
                raise RuntimeError(
                    f"Worktree collision: {worktree_path} belongs to '{owner_id}', "
                    f"not '{task_id}' (both map to safe name '{safe_task}')"
                )
        log_event(log_path, "INFO", "task worktree reused",
                  task_id=task_id, worktree_path=str(worktree_path))
        return WorktreeSession(
            base_workdir=base_workdir,
            worktree_path=str(worktree_path),
            branch_name=branch_name,
            task_id=task_id,
            reused=True,
        )

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
                raise RuntimeError(
                    f"worktree reset to {main_branch} failed for {task_id}: {stderr_r.strip()[:200]}"
                )
        else:
            raise RuntimeError(f"failed to create worktree: {stderr.strip()} / {stderr2.strip()}")
    # Write card ID ownership marker to prevent _safe_name collisions
    try:
        (worktree_path / ".orc-card-id").write_text(task_id, encoding="utf-8")
    except OSError:
        pass
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
    # Keep the task branch as a safety net — commits stay reachable
    # even if cherry-pick to main was missed or incomplete.
    if session.branch_name:
        log_event(log_path, "INFO", "task branch preserved",
                  task_id=session.task_id, branch=session.branch_name)
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


def _list_commit_files(workdir: str, commit_sha: str) -> list[str]:
    ok, stdout, _, _ = run_git(workdir, ["git", "show", "--pretty=format:", "--name-only", commit_sha])
    if not ok:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def _is_orchestration_only_path(path: str) -> bool:
    normalized = (path or "").strip()
    return normalized.startswith("tasks/") or _is_runtime_artifact_path(normalized)


def resolve_integration_commit(workdir: str, main_branch: str) -> str:
    """
    Resolve the commit that should be integrated into main.

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
    main_branch: str = DEFAULT_MAIN_BRANCH,
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


def _is_branch_merged(workdir: str, branch: str, main_branch: str) -> bool:
    """Check if all code changes from branch are already in main_branch.

    Uses merge-base comparison: finds files changed on branch since fork,
    then checks if main has identical content.  Three-dot diff does NOT work
    after squash-merge (branch is not an ancestor of main).
    """
    # Find merge base
    ok_mb, mb_out, _, _ = run_git(workdir, ["git", "merge-base", main_branch, branch])
    if not ok_mb:
        return False
    merge_base = mb_out.strip()
    # Files changed on branch since fork
    ok_files, files_out, _, _ = run_git(
        workdir, ["git", "diff", "--name-only", merge_base, branch, "--", ".", ":!tasks/"],
    )
    if not ok_files:
        return False
    branch_files = [f.strip() for f in files_out.splitlines() if f.strip()]
    if not branch_files:
        return True  # no code changes on branch
    # Check if main has identical content for those files
    diff_cmd = ["git", "diff", branch, main_branch, "--"] + branch_files
    ok_diff, diff_out, _, _ = run_git(workdir, diff_cmd)
    if not ok_diff:
        return False
    return not bool(diff_out.strip())


def _squash_merge_branch(workdir: str, branch: str) -> tuple[bool, bool, str]:
    """Run git merge --squash. Returns (ok, has_conflict, error)."""
    ok, _, stderr, _ = run_git(workdir, ["git", "merge", "--squash", branch])
    if ok:
        return True, False, ""
    lowered = (stderr or "").lower()
    # Check for merge conflicts
    ok_conflicts, conflict_files, _, _ = run_git(
        workdir, ["git", "diff", "--name-only", "--diff-filter=U"],
    )
    if ok_conflicts and bool(conflict_files.strip()):
        return False, True, stderr.strip()
    if "conflict" in lowered:
        return False, True, stderr.strip()
    return False, False, stderr.strip()


def merge_task_branch_into_main(
    *,
    base_workdir: str,
    branch_name: str,
    task_id: str,
    task_title: str,
    log_path: Path,
    main_branch: str = DEFAULT_MAIN_BRANCH,
    skip_preflight: bool = False,
) -> IntegrationResult:
    """Squash-merge task branch into main.

    Unlike cherry-pick, this captures ALL commits on the branch in a single
    merge commit.  No work is lost regardless of how many commits the agent made.
    """
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

    # Check if branch exists
    ok_branch, _, _, _ = run_git(base_workdir, ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"])
    if not ok_branch:
        return IntegrationResult(ok=False, conflict=False, error=f"task branch '{branch_name}' not found")

    # Check if already fully merged
    if _is_branch_merged(base_workdir, branch_name, main_branch):
        log_event(
            log_path,
            "INFO",
            "task branch already merged in main",
            task_id=task_id,
            branch=branch_name,
            main_branch=main_branch,
        )
        return IntegrationResult(ok=True, conflict=False, already_integrated=True)

    ok_merge, has_conflict, merge_error = _squash_merge_branch(base_workdir, branch_name)
    if not ok_merge and not has_conflict:
        return IntegrationResult(ok=False, conflict=False, error=merge_error)
    if has_conflict:
        log_event(
            log_path,
            "WARN",
            "merge conflict while integrating task branch",
            task_id=task_id,
            branch=branch_name,
            main_branch=main_branch,
            error=merge_error[:500],
        )
        return IntegrationResult(ok=False, conflict=True, error=merge_error)

    # Exclude tasks/ from the merge — worktree has its own card copies
    # that diverge from main's board state, causing spurious conflicts.
    import os
    tasks_dir = os.path.join(base_workdir, "tasks")
    if os.path.isdir(tasks_dir):
        run_git(base_workdir, ["git", "checkout", "HEAD", "--", "tasks/"])
        log_event(log_path, "INFO", "excluded tasks/ from squash merge",
                  task_id=task_id, branch=branch_name)

    # Squash merge stages changes but doesn't commit — commit now
    safe_title = (task_title or task_id).replace('"', "'")[:200]
    commit_msg = f"feat({task_id}): {safe_title}"
    ok_commit, _, stderr_commit, _ = run_git(
        base_workdir, ["git", "commit", "-m", commit_msg],
    )
    if not ok_commit:
        # Nothing to commit = already integrated
        if "nothing to commit" in (stderr_commit or "").lower():
            log_event(log_path, "INFO", "squash merge produced empty commit; already integrated",
                      task_id=task_id, branch=branch_name)
            return IntegrationResult(ok=True, conflict=False, already_integrated=True)
        return IntegrationResult(ok=False, conflict=False, error=f"commit after squash merge failed: {stderr_commit.strip()}")

    log_event(
        log_path,
        "INFO",
        "task branch integrated in main via squash merge",
        task_id=task_id,
        branch=branch_name,
        main_branch=main_branch,
    )
    return IntegrationResult(ok=True, conflict=False)


def abort_merge(workdir: str) -> bool:
    """Abort an in-progress merge (squash or regular)."""
    # git merge --squash doesn't set MERGE_HEAD, so --abort may not work.
    # Use reset --merge which always works.
    ok, _, _, _ = run_git(workdir, ["git", "reset", "--merge"])
    return ok
