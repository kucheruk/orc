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

# Per-worktree git attribute lines written into .git/worktrees/<name>/info/attributes.
# `tasks/**` is the kanban board that master keeps moving between stage folders
# via auto-commit. Agent-driven `git merge master --no-edit` in an isolated
# worktree branch (forked when the card was in an earlier stage) then produces
# a rename-modify conflict on the card's own file and leaves `<<<<<<<`
# markers that the agent commits verbatim — blocking review/test and
# burning a full bounceback cycle. `merge=ours` tells git to always keep the
# worktree-branch side for tasks/ files, so downstream merges resolve cleanly
# without agent intervention. ORC re-syncs the canonical card copy into the
# worktree before each agent run regardless, so "ours wins" does not mask
# real board state from the agent.
_WORKTREE_MERGE_ATTRIBUTES = (
    "# Managed by ORC create_task_worktree — keep kanban card files on the\n"
    "# worktree-branch side during any `git merge`. See orc_core/git/worktree_lifecycle.py.\n"
    "tasks/**    merge=ours\n"
)


def _apply_worktree_merge_attributes(worktree_path: Path, log_path: Path, *, task_id: str) -> None:
    """Write the worktree-scoped merge attributes so tasks/ files auto-resolve
    to ours on any subsequent `git merge master` the agent runs.

    `$GIT_DIR` for a linked worktree is `.git/worktrees/<name>/` and its
    `info/attributes` is consulted alongside (but separately from) the
    committed `.gitattributes`, so we do not pollute the branch history.
    Also register the `ours` merge driver (git does not ship one by default
    under that exact name unless configured) via `git config merge.ours.driver`
    scoped to the worktree. Idempotent across worktree re-use.
    """
    ok_dir, git_dir_raw, _, _ = run_git(str(worktree_path), ["git", "rev-parse", "--git-dir"])
    if not ok_dir:
        log_event(log_path, "WARN", "worktree merge attrs: rev-parse --git-dir failed",
                  task_id=task_id, worktree_path=str(worktree_path))
        return
    git_dir = Path(git_dir_raw.strip())
    if not git_dir.is_absolute():
        git_dir = (worktree_path / git_dir).resolve()
    info_dir = git_dir / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    attrs_path = info_dir / "attributes"
    current = attrs_path.read_text(encoding="utf-8") if attrs_path.exists() else ""
    if "tasks/**    merge=ours" not in current:
        attrs_path.write_text(
            (current.rstrip() + "\n" if current.strip() else "") + _WORKTREE_MERGE_ATTRIBUTES,
            encoding="utf-8",
        )
    # `merge=ours` is a named driver, not the `-s ours` strategy. Point it at
    # `true` so git keeps the ours version for tasks/ files without complaint.
    run_git(str(worktree_path), ["git", "config", "--worktree", "merge.ours.name", "Keep ours"])
    run_git(str(worktree_path), ["git", "config", "--worktree", "merge.ours.driver", "true"])
    log_event(log_path, "INFO", "worktree merge attrs applied",
              task_id=task_id, attrs_path=str(attrs_path))


def _list_worktree_branches(workdir: str) -> dict[str, str]:
    """Return {resolved_worktree_path: short_branch_name} per `git worktree list --porcelain`.

    Detached heads map to `""` so collision detection can distinguish
    "no branch" from "some other branch". Paths are resolved so callers
    can match regardless of symlink/normalization differences.
    """
    ok, stdout, _, _ = run_git(workdir, ["git", "worktree", "list", "--porcelain"])
    if not ok:
        return {}
    result: dict[str, str] = {}
    current_path = ""
    for raw in stdout.splitlines():
        line = raw.rstrip()
        if line.startswith("worktree "):
            current_path = str(Path(line[len("worktree "):].strip()).resolve())
            result.setdefault(current_path, "")
        elif line.startswith("branch ") and current_path:
            ref = line[len("branch "):].strip()
            if ref.startswith("refs/heads/"):
                result[current_path] = ref[len("refs/heads/"):]
            else:
                result[current_path] = ref
        elif not line.strip():
            current_path = ""
    return result


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
        target_key = str(worktree_path.resolve())
        registered = _list_worktree_branches(base_workdir).get(target_key)
        if registered == branch_name:
            log_event(log_path, "INFO", "task worktree reused",
                      task_id=task_id, worktree_path=str(worktree_path))
            _apply_worktree_merge_attributes(worktree_path, log_path, task_id=task_id)
            return WorktreeSession(
                base_workdir=base_workdir,
                worktree_path=str(worktree_path),
                branch_name=branch_name,
                task_id=task_id,
                reused=True,
            )
        if registered is None:
            reason = "orphaned on disk"
        elif registered == "":
            reason = "parked on a detached HEAD"
        else:
            reason = f"registered to branch '{registered}'"
        log_event(log_path, "ERROR", "worktree collision detected",
                  task_id=task_id, registered_branch=registered or "",
                  safe_name=safe_task, worktree_path=str(worktree_path))
        raise RuntimeError(
            f"Worktree collision: {worktree_path} is {reason}, not "
            f"'{branch_name}'; run `git worktree prune` in {base_workdir} "
            f"or remove the directory manually"
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
    log_event(
        log_path,
        "INFO",
        "task worktree created",
        task_id=task_id,
        worktree_path=str(worktree_path),
        branch_name=branch_name,
    )
    _apply_worktree_merge_attributes(worktree_path, log_path, task_id=task_id)
    return WorktreeSession(
        base_workdir=base_workdir,
        worktree_path=str(worktree_path),
        branch_name=branch_name,
        task_id=task_id,
    )


def cleanup_task_worktree(session: WorktreeSession, log_path: Path, *, force: bool = False) -> None:
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
        if not (only_runtime_artifacts or force):
            raise RuntimeError(f"failed to remove worktree: {stderr.strip()}")
        fallback_reason = "force remove requested" if force else "force remove due to runtime artifacts"
        log_event(
            log_path,
            "WARN",
            f"worktree cleanup fallback: {fallback_reason}",
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
