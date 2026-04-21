#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manages squash-merge integration of task branches into main branch."""

import logging
import threading

_logger = logging.getLogger(__name__)
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..infra.io.atomic_io import write_json_atomic
from ..log import log_event
from ..errors.truncation import (
    ERROR_TRUNCATE,
    REASON_TRUNCATE,
    TRACEBACK_TRUNCATE,
)
from ..infra.io.state_paths import integration_report_path
from ..tasks.dto import Task
from .conflict_resolver import ConflictResolver
from .ports import ConflictResolverPort, GitRunner, SafeFilesGuardPort
from .safe_files import SafeFilesGuard
from .subprocess_git import SubprocessGitRunner
from .branch_merger import abort_merge, merge_task_branch_into_main
from .integration_preflight import preflight_main_integration


@dataclass
class IntegrationContext:
    """Bundles state for a single integration attempt."""
    session_id: str
    task_id: str
    workdir: str
    main_branch: str
    log_path: Path
    commit_sha: str = ""
    report: dict = field(default_factory=dict)

    def __post_init__(self):
        self.report = {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "started_at": datetime.now().isoformat(),
            "steps": [],
        }

    def step(self, name: str, **data) -> None:
        entry = {"step": name, "at": datetime.now().isoformat(), **data}
        self.report["steps"].append(entry)
        log_event(self.log_path, "INFO", f"integration:{name}",
                  session_id=self.session_id, task_id=self.task_id, **data)

    def step_error(self, name: str, **data) -> None:
        entry = {"step": name, "at": datetime.now().isoformat(), "error": True, **data}
        self.report["steps"].append(entry)
        log_event(self.log_path, "ERROR", f"integration:{name}",
                  session_id=self.session_id, task_id=self.task_id, **data)

    def save_report(self, status: str, reason: str = "") -> None:
        self.report["finished_at"] = datetime.now().isoformat()
        self.report["status"] = status
        self.report["reason"] = reason
        rpath = integration_report_path(self.workdir, self.session_id, self.task_id)
        rpath.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(rpath, self.report)


class IntegrationManager:
    """Serializes squash-merge integration of task branches into main."""

    def __init__(self, *, workdir: str, main_branch: str, log_path: Path,
                 safe_tracked_paths: frozenset[str] = frozenset(),
                 git: Optional[GitRunner] = None,
                 conflicts: Optional[ConflictResolverPort] = None,
                 safe_files: Optional[SafeFilesGuardPort] = None) -> None:
        self.workdir = workdir
        self.main_branch = main_branch
        self.log_path = log_path
        self._safe_tracked_paths = safe_tracked_paths
        self._git: GitRunner = git or SubprocessGitRunner()
        self._safe_files: SafeFilesGuardPort = safe_files or SafeFilesGuard(
            workdir, safe_tracked_paths, log_path=log_path,
        )
        self._lock = threading.Lock()
        self._conflict_resolver: ConflictResolverPort = conflicts or ConflictResolver(workdir)

    def integrate(
        self,
        session_id: str,
        task: Task,
        execution_workdir: str,
        merge_expert_fn: Optional[Callable[[], bool]] = None,
        status_fn: Optional[Callable[[str], None]] = None,
        branch_name: str = "",
    ) -> bool:
        """Squash-merge a task branch into main.

        ``execution_workdir`` is optional: when empty the caller must supply
        ``branch_name`` directly. This lets the integration path run even when
        the WorktreeSession was lost (e.g. after an ORC restart between an
        agent writing ``action=Done`` and the session cleanup firing).
        """
        notify = status_fn or (lambda _msg: None)
        ctx = IntegrationContext(
            session_id=session_id,
            task_id=task.task_id,
            workdir=self.workdir,
            main_branch=self.main_branch,
            log_path=self.log_path,
        )
        notify(f"Waiting for integration lock ({task.task_id})...")
        with self._lock:
            notify(f"Squash-merging {task.task_id} into {self.main_branch}...")
            try:
                return self._execute(ctx, execution_workdir, task, merge_expert_fn, branch_name)
            except Exception as exc:
                ctx.step_error("unexpected_exception",
                               error=str(exc),
                               tb=traceback.format_exc()[:TRACEBACK_TRUNCATE])
                self._abort_merge(ctx)
                ctx.save_report("failed", f"unexpected_exception:{type(exc).__name__}")
                return False

    def recover_stale_git_state(self) -> None:
        # Resolve actual git dir (handles worktrees where .git is a file)
        ok, git_dir_out, _, _ = self._git.run(self.workdir, ["git", "rev-parse", "--git-dir"])
        if ok:
            git_dir = Path(git_dir_out.strip())
            if not git_dir.is_absolute():
                git_dir = Path(self.workdir) / git_dir
        else:
            git_dir = Path(self.workdir) / ".git"
        # SQUASH_MSG is left by git merge --squash; clean it via reset --merge
        squash_msg = git_dir / "SQUASH_MSG"
        if squash_msg.exists():
            log_event(self.log_path, "WARN", "stale SQUASH_MSG detected, resetting",
                      workdir=self.workdir)
            abort_merge(self.workdir)
            if squash_msg.exists():
                squash_msg.unlink(missing_ok=True)
        for marker, abort_cmd in [
            ("CHERRY_PICK_HEAD", ["git", "cherry-pick", "--abort"]),
            ("MERGE_HEAD", ["git", "merge", "--abort"]),
            ("REBASE_HEAD", ["git", "rebase", "--abort"]),
        ]:
            marker_path = git_dir / marker
            if not marker_path.exists():
                continue
            log_event(self.log_path, "WARN", f"stale {marker} detected, aborting",
                      workdir=self.workdir)
            ok, _, stderr, _ = self._git.run(self.workdir, abort_cmd)
            if ok:
                log_event(self.log_path, "INFO", f"stale {marker} aborted")
            else:
                log_event(self.log_path, "ERROR", f"failed to abort stale {marker}",
                          stderr=stderr[:ERROR_TRUNCATE])
                self._safe_files.hard_reset_preserving()

    # ── Private ──────────────────────────────────────────────────

    def _execute(
        self,
        ctx: IntegrationContext,
        execution_workdir: str,
        task: Task,
        merge_expert_fn: Optional[Callable],
        explicit_branch: str = "",
    ) -> bool:
        branch_name = (explicit_branch or "").strip()
        if not branch_name or branch_name == "HEAD":
            ctx.step_error("branch_resolve_failed", worktree=execution_workdir)
            ctx.save_report("failed", "branch_resolve_failed")
            return False
        if not self._has_commits(ctx, branch_name):
            return False
        ctx.report["branch"] = branch_name
        stashed = self._stash_dirty_state(ctx)
        try:
            if not self._preflight(ctx):
                return False
            saved = self._stash_safe_files(ctx)
            try:
                result = self._squash_merge_with_retry(ctx, branch_name, task, merge_expert_fn)
            finally:
                self._restore_safe_files(ctx, saved)
            return result
        finally:
            if stashed:
                self._pop_stash(ctx)

    def _stash_dirty_state(self, ctx: IntegrationContext) -> bool:
        """Stash any dirty working-tree state so cherry-pick has a clean base.

        Returns True if a stash was created. The caller MUST call _pop_stash()
        in a finally block to restore the user's changes.
        """
        # Quick check: is there anything to stash?
        ok, stdout, _, _ = self._git.run(self.workdir, ["git", "status", "--porcelain"])
        if not ok or not stdout.strip():
            return False
        ok_stash, _, stderr, _ = self._git.run(
            self.workdir,
            ["git", "stash", "push", "--include-untracked", "-m", "orc-integration-autostash"],
        )
        if ok_stash:
            ctx.step("autostash_created")
            return True
        ctx.step("autostash_failed", stderr=stderr[:ERROR_TRUNCATE])
        return False

    def _pop_stash(self, ctx: IntegrationContext) -> None:
        """Restore stashed state after cherry-pick. Conflicts are left for user."""
        ok, _, stderr, _ = self._git.run(self.workdir, ["git", "stash", "pop"])
        if ok:
            ctx.step("autostash_restored")
        else:
            # Pop failed (conflict with cherry-picked changes). The stash is
            # still on the stack. Try to apply instead — git stash apply leaves
            # the stash so nothing is lost even if working-tree conflicts remain.
            ok_apply, _, stderr_apply, _ = self._git.run(self.workdir, ["git", "stash", "apply"])
            if ok_apply:
                ctx.step("autostash_applied_with_conflicts")
                # Drop the stash entry since apply succeeded
                self._git.run(self.workdir, ["git", "stash", "drop"])
            else:
                ctx.step("autostash_pop_failed", stderr=stderr_apply[:ERROR_TRUNCATE])
                log_event(self.log_path, "WARN",
                          "autostash pop/apply failed — stash preserved, run 'git stash pop' manually",
                          workdir=self.workdir)

    def _stash_safe_files(self, ctx: IntegrationContext) -> dict[str, str]:
        saved = self._safe_files.save()
        if saved:
            ctx.step("stashed_safe_files", files=list(saved.keys()))
        return saved

    def _restore_safe_files(self, ctx: IntegrationContext, saved: dict[str, str]) -> None:
        if not saved:
            return
        self._safe_files.restore(saved)
        ctx.step("restored_safe_files", files=list(saved.keys()))

    def _preflight(self, ctx: IntegrationContext) -> bool:
        ctx.step("preflight_start")
        result = preflight_main_integration(
            base_workdir=self.workdir, main_branch=self.main_branch,
            extra_safe_paths=self._safe_tracked_paths)
        if not result.ok:
            ctx.step_error("preflight_failed", error=result.error)
            ctx.save_report("failed", f"preflight_failed:{result.error[:REASON_TRUNCATE]}")
            return False
        ctx.step("preflight_ok")
        return True

    def _has_commits(self, ctx: IntegrationContext, branch_name: str) -> bool:
        """Check the task branch has code commits vs main.

        Queried from the main workdir against ``{main_branch}..{branch_name}``
        so the check works whether or not a worktree is checked out on the
        branch — required for the orphan-recovery path where the
        WorktreeSession was lost after an ORC restart.
        """
        # Probe the branch ref first. rev-list against a missing ref also
        # fails, but surfacing "branch_missing" separately lets callers
        # distinguish "nothing to merge, give up" from "git is in a weird
        # state, retry later".
        ok_ref, _, _, _ = self._git.run(
            self.workdir,
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        )
        if not ok_ref:
            ctx.step_error("branch_missing", branch=branch_name)
            ctx.save_report("failed", "branch_missing")
            return False
        ok, stdout, stderr, _ = self._git.run(
            self.workdir,
            ["git", "rev-list", "--count", f"{self.main_branch}..{branch_name}"],
        )
        if not ok:
            ctx.step_error("ahead_count_failed", branch=branch_name, error=stderr[:200])
            ctx.save_report("failed", "ahead_count_failed")
            return False
        try:
            ahead = int((stdout or "0").strip() or "0")
        except ValueError:
            ahead = 0
        if ahead <= 0:
            ctx.step_error("no_commits_ahead", branch=branch_name)
            ctx.save_report("failed", "no_commits_ahead")
            return False
        # Commits exist — require at least one of them to touch code outside tasks/.
        ok_diff, diff_out, _, _ = self._git.run(
            self.workdir,
            ["git", "diff", "--name-only", f"{self.main_branch}..{branch_name}", "--", ".", ":!tasks/"],
        )
        changed = [line for line in (diff_out or "").splitlines() if line.strip()] if ok_diff else []
        if not changed:
            ctx.step_error("no_code_changes",
                           branch=branch_name,
                           detail="commits exist but only contain card/task file changes")
            ctx.save_report("failed", "no_code_changes")
            return False
        return True

    def _squash_merge_with_retry(
        self, ctx: IntegrationContext, branch_name: str, task: Task,
        merge_expert_fn: Optional[Callable],
    ) -> bool:
        ctx.step("squash_merge_attempt", attempt=1, branch=branch_name)
        result = merge_task_branch_into_main(
            base_workdir=self.workdir, branch_name=branch_name,
            task_id=ctx.task_id, task_title=task.text or ctx.task_id,
            log_path=self.log_path, main_branch=self.main_branch,
            skip_preflight=True)

        if result.ok:
            ctx.step("squash_merge_ok", attempt=1, already=result.already_integrated)
            ctx.save_report("completed", "squash_merge_ok")
            return True

        if not result.conflict:
            ctx.step_error("squash_merge_failed_no_conflict", error=result.error[:ERROR_TRUNCATE])
            self._abort_merge(ctx)
            ctx.save_report("failed", f"squash_merge_error:{result.error[:REASON_TRUNCATE]}")
            return False

        return self._conflict_resolver.resolve(ctx, result, merge_expert_fn, self._abort_merge)

    def _git_dir(self) -> Path:
        """Resolve the actual .git directory (handles worktrees)."""
        ok, out, _, _ = self._git.run(self.workdir, ["git", "rev-parse", "--git-dir"])
        if ok:
            p = Path(out.strip())
            return p if p.is_absolute() else Path(self.workdir) / p
        return Path(self.workdir) / ".git"

    def _abort_merge(self, ctx: IntegrationContext) -> None:
        if abort_merge(self.workdir):
            ctx.step("merge_aborted")
            return
        # Fallback: try cherry-pick abort in case of stale state
        ok, _, stderr, _ = self._git.run(self.workdir, ["git", "cherry-pick", "--abort"])
        if ok:
            ctx.step("cherry_pick_aborted")
            return
        ctx.step_error("merge_abort_failed", stderr=stderr[:ERROR_TRUNCATE])
        self._hard_reset_preserving_safe_files(ctx)

    def _hard_reset_preserving_safe_files(self, ctx: IntegrationContext) -> None:
        preserved = self._safe_files.hard_reset_preserving()
        ctx.step("hard_reset_with_preserved_files", preserved=preserved)
