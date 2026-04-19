#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git worktree creation and teardown."""

from __future__ import annotations

from pathlib import Path

from ..infra.io.state_paths import worktrees_root
from ..log import log_event
from .branch_resolver import DEFAULT_MAIN_BRANCH, _safe_name, task_branch_name
from .git_dto import WorktreeSession
from .git_helpers import is_runtime_artifact, run_git


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
        ok2, _, stderr2, _ = run_git(
            base_workdir,
            ["git", "worktree", "add", str(worktree_path), branch_name],
        )
        if not ok2:
            raise RuntimeError(f"failed to create worktree: {stderr.strip()} / {stderr2.strip()}")
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
        only_runtime_artifacts = bool(dirty_paths) and all(is_runtime_artifact(path) for path in dirty_paths)
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
