#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Branch integration: cherry-pick and squash-merge into main."""

from __future__ import annotations

import os
from pathlib import Path

from ..log import log_event
from .branch_resolver import DEFAULT_MAIN_BRANCH
from .git_dto import IntegrationResult
from .git_helpers import integration_commit_message, run_git
from .integration_preflight import preflight_main_integration


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


def _is_commit_in_branch(workdir: str, commit_sha: str, branch: str) -> bool:
    ok, _, _, _ = run_git(workdir, ["git", "merge-base", "--is-ancestor", commit_sha, branch])
    return ok


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
    then checks if main has identical content. Three-dot diff does NOT work
    after squash-merge (branch is not an ancestor of main).
    """
    ok_mb, mb_out, _, _ = run_git(workdir, ["git", "merge-base", main_branch, branch])
    if not ok_mb:
        return False
    merge_base = mb_out.strip()
    ok_files, files_out, _, _ = run_git(
        workdir, ["git", "diff", "--name-only", merge_base, branch, "--", ".", ":!tasks/"],
    )
    if not ok_files:
        return False
    branch_files = [f.strip() for f in files_out.splitlines() if f.strip()]
    if not branch_files:
        return True
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
    merge commit. No work is lost regardless of how many commits the agent made.
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

    ok_branch, _, _, _ = run_git(base_workdir, ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"])
    if not ok_branch:
        return IntegrationResult(ok=False, conflict=False, error=f"task branch '{branch_name}' not found")

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

    tasks_dir = os.path.join(base_workdir, "tasks")
    if os.path.isdir(tasks_dir):
        # `git checkout HEAD -- tasks/` only reverts modifications to
        # tracked files. Newly-added files brought in by the squash
        # merge (common when the worktree was created at a moment when
        # the tasks/ layout differed from current main — e.g. another
        # card had moved from 6_Testing to 7_Handoff and the stale
        # copy still lives on the worktree branch) stay staged and
        # land in main. Observed on jeeves 2026-04-20: EMP-002's
        # integrator merge added a stale 7_Handoff/NOTIF-002-C-B.md
        # containing three concatenated frontmatter blocks, creating
        # a duplicate card alongside the real 5_Review copy.
        #
        # Reset the whole tasks/ subtree to HEAD: `git rm -rf --cached`
        # drops every added/modified tasks/ path from the merge index,
        # `git checkout HEAD -- tasks/` restores the files from HEAD,
        # and `git clean -fdx tasks/` wipes any untracked leftovers
        # from the worktree merge that were never staged. The net is
        # that tasks/ after the merge is byte-identical to main HEAD.
        run_git(base_workdir, ["git", "rm", "-rf", "--cached", "--quiet", "--ignore-unmatch", "tasks/"])
        run_git(base_workdir, ["git", "checkout", "HEAD", "--", "tasks/"])
        run_git(base_workdir, ["git", "clean", "-fdx", "--", "tasks/"])
        log_event(log_path, "INFO", "excluded tasks/ from squash merge",
                  task_id=task_id, branch=branch_name)

    commit_msg = integration_commit_message(task_id, task_title)
    ok_commit, _, stderr_commit, _ = run_git(
        base_workdir, ["git", "commit", "-m", commit_msg],
    )
    if not ok_commit:
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
    ok, _, _, _ = run_git(workdir, ["git", "reset", "--merge"])
    return ok
