#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Branch integration: squash-merge task branches into main."""

from __future__ import annotations

import os
from pathlib import Path

from ..log import log_event
from .branch_resolver import DEFAULT_MAIN_BRANCH
from .git_dto import IntegrationResult
from .git_helpers import integration_commit_message, run_git
from .integration_preflight import preflight_main_integration


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

    Captures ALL commits on the branch in a single merge commit, so no
    work is lost regardless of how many commits the agent made.
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
        # Conflicts confined to tasks/ are board-state churn, not real
        # integration disagreement: the worktree's AutoCommitStep writes
        # tasks/*.md continuously (card-state telemetry) while main's
        # AutoCommitStep writes the exact same files in parallel from
        # unrelated cards. The merge-commit that lands on main explicitly
        # drops tasks/ changes (see the `git checkout HEAD -- tasks/`
        # block below), so carrying these conflicts into the
        # merge-expert path burns an LLM turn and a retry cycle for zero
        # benefit — the conflict files would be discarded anyway.
        #
        # Observed live on jeeves 2026-04-20: QA-001-A hit this path
        # with 6 conflicts all in tasks/ (other cards' frontmatter). No
        # merge_expert_fn was wired, so the card auto-blocked after
        # 3 retries despite the only real obstacle being board-state
        # churn. Deal with the known-noisy case in-line and leave the
        # conflict=True return strictly for real code-level merges.
        ok_list, conflict_paths_raw, _, _ = run_git(
            base_workdir, ["git", "diff", "--name-only", "--diff-filter=U"]
        )
        conflict_paths = (
            [p for p in conflict_paths_raw.strip().splitlines() if p.strip()]
            if ok_list else []
        )
        non_tasks = [p for p in conflict_paths if not p.startswith("tasks/")]
        if conflict_paths and not non_tasks:
            # Every conflict is in tasks/. Accept HEAD's version across
            # the entire subtree (exactly what the post-merge reset
            # does on the happy path) and let the commit continue.
            run_git(base_workdir, ["git", "rm", "-rf", "--cached", "--quiet", "--ignore-unmatch", "tasks/"])
            run_git(base_workdir, ["git", "checkout", "HEAD", "--", "tasks/"])
            run_git(base_workdir, ["git", "clean", "-fdx", "--", "tasks/"])
            log_event(
                log_path,
                "INFO",
                "merge conflict confined to tasks/ — auto-resolved to HEAD",
                task_id=task_id,
                branch=branch_name,
                resolved_paths=conflict_paths[:20],
            )
            # Fall through to the commit block below.
        else:
            log_event(
                log_path,
                "WARN",
                "merge conflict while integrating task branch",
                task_id=task_id,
                branch=branch_name,
                main_branch=main_branch,
                error=merge_error[:500],
                non_tasks_conflicts=non_tasks[:20],
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
