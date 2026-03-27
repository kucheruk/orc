#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manages cherry-pick integration of task commits into main branch."""

import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .atomic_io import write_json_atomic
from .logging import log_event
from .session_types import (
    ERROR_TRUNCATE,
    CONFLICT_ERROR_TRUNCATE,
    REASON_TRUNCATE,
    TRACEBACK_TRUNCATE,
    SessionSlot,
)
from .state_paths import integration_report_path
from .task_execution import has_commits_ahead_of_branch
from .task_source import Task
from .worktree_flow import (
    get_head_commit,
    integrate_commit_into_main,
    preflight_main_integration,
    run_git,
)


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
    """Serializes cherry-pick integration of task commits into main."""

    def __init__(self, *, workdir: str, main_branch: str, log_path: Path) -> None:
        self.workdir = workdir
        self.main_branch = main_branch
        self.log_path = log_path
        self._lock = threading.Lock()

    def integrate(
        self,
        slot: SessionSlot,
        task: Task,
        execution_workdir: str,
        merge_expert_fn: Optional[Callable[[SessionSlot, Task], bool]] = None,
    ) -> bool:
        ctx = IntegrationContext(
            session_id=slot.session_id,
            task_id=task.task_id,
            workdir=self.workdir,
            main_branch=self.main_branch,
            log_path=self.log_path,
        )
        with self._lock:
            try:
                return self._execute(ctx, execution_workdir, merge_expert_fn)
            except Exception as exc:
                ctx.step_error("unexpected_exception",
                               error=str(exc),
                               tb=traceback.format_exc()[:TRACEBACK_TRUNCATE])
                self._abort_cherry_pick(ctx)
                ctx.save_report("failed", f"unexpected_exception:{type(exc).__name__}")
                return False

    def recover_stale_git_state(self) -> None:
        for marker, abort_cmd in [
            ("CHERRY_PICK_HEAD", ["git", "cherry-pick", "--abort"]),
            ("MERGE_HEAD", ["git", "merge", "--abort"]),
        ]:
            marker_path = Path(self.workdir) / ".git" / marker
            if not marker_path.exists():
                continue
            log_event(self.log_path, "WARN", f"stale {marker} detected, aborting",
                      workdir=self.workdir)
            ok, _, stderr, _ = run_git(self.workdir, abort_cmd)
            if ok:
                log_event(self.log_path, "INFO", f"stale {marker} aborted")
            else:
                log_event(self.log_path, "ERROR", f"failed to abort stale {marker}",
                          stderr=stderr[:ERROR_TRUNCATE])
                run_git(self.workdir, ["git", "reset", "--hard", "HEAD"])
                log_event(self.log_path, "WARN", "hard reset to recover from stale state")

    # ── Private ──────────────────────────────────────────────────

    def _execute(
        self,
        ctx: IntegrationContext,
        execution_workdir: str,
        merge_expert_fn: Optional[Callable],
    ) -> bool:
        if not self._preflight(ctx):
            return False
        if not self._has_commits(ctx, execution_workdir):
            return True
        if not self._resolve_commit(ctx, execution_workdir):
            return False
        return self._cherry_pick_with_retry(ctx, merge_expert_fn)

    def _preflight(self, ctx: IntegrationContext) -> bool:
        ctx.step("preflight_start")
        result = preflight_main_integration(
            base_workdir=self.workdir, main_branch=self.main_branch)
        if not result.ok:
            ctx.step_error("preflight_failed", error=result.error)
            ctx.save_report("failed", f"preflight_failed:{result.error[:REASON_TRUNCATE]}")
            return False
        ctx.step("preflight_ok")
        return True

    def _has_commits(self, ctx: IntegrationContext, execution_workdir: str) -> bool:
        if has_commits_ahead_of_branch(execution_workdir, self.main_branch, self.log_path):
            return True
        ctx.step("no_commits_ahead", worktree=execution_workdir)
        ctx.save_report("skipped", "no_commits_ahead")
        return False

    def _resolve_commit(self, ctx: IntegrationContext, execution_workdir: str) -> bool:
        try:
            ctx.commit_sha = get_head_commit(execution_workdir)
        except Exception as exc:
            ctx.step_error("get_commit_sha_failed", error=str(exc))
            ctx.save_report("failed", "get_commit_sha_failed")
            return False
        ctx.step("commit_sha_resolved", commit_sha=ctx.commit_sha)
        ctx.report["commit_sha"] = ctx.commit_sha
        return True

    def _cherry_pick_with_retry(self, ctx: IntegrationContext, merge_expert_fn: Optional[Callable]) -> bool:
        ctx.step("cherry_pick_attempt", attempt=1)
        result = integrate_commit_into_main(
            base_workdir=self.workdir, commit_sha=ctx.commit_sha,
            task_id=ctx.task_id, log_path=self.log_path,
            main_branch=self.main_branch)

        if result.ok:
            ctx.step("cherry_pick_ok", attempt=1, already=result.already_integrated)
            ctx.save_report("completed", "cherry_pick_ok")
            return True

        if not result.conflict:
            ctx.step_error("cherry_pick_failed_no_conflict", error=result.error[:ERROR_TRUNCATE])
            self._abort_cherry_pick(ctx)
            ctx.save_report("failed", f"cherry_pick_error:{result.error[:REASON_TRUNCATE]}")
            return False

        return self._resolve_conflict_and_retry(ctx, result, merge_expert_fn)

    def _resolve_conflict_and_retry(self, ctx: IntegrationContext, initial_attempt, merge_expert_fn: Optional[Callable]) -> bool:
        ctx.step("conflict_detected", error=initial_attempt.error[:CONFLICT_ERROR_TRUNCATE])
        self._log_conflict_files(ctx)

        if not self._invoke_merge_expert(ctx, merge_expert_fn):
            return False

        return self._retry_cherry_pick(ctx)

    def _invoke_merge_expert(self, ctx: IntegrationContext, merge_expert_fn: Optional[Callable]) -> bool:
        if not merge_expert_fn:
            ctx.step_error("no_merge_expert_available")
            self._abort_cherry_pick(ctx)
            ctx.save_report("failed", "no_merge_expert")
            return False

        ctx.step("merge_expert_start")
        if not merge_expert_fn():
            ctx.step_error("merge_expert_failed")
            self._abort_cherry_pick(ctx)
            ctx.save_report("failed", "merge_expert_failed")
            return False

        ctx.step("merge_expert_completed")
        return True

    def _retry_cherry_pick(self, ctx: IntegrationContext) -> bool:
        ctx.step("cherry_pick_attempt", attempt=2)
        retry_result = integrate_commit_into_main(
            base_workdir=self.workdir, commit_sha=ctx.commit_sha,
            task_id=ctx.task_id, log_path=self.log_path,
            main_branch=self.main_branch)

        if retry_result.ok:
            ctx.step("cherry_pick_ok", attempt=2)
            ctx.save_report("completed", "cherry_pick_ok_after_merge_expert")
            return True

        ctx.step_error("cherry_pick_failed_after_expert",
                       error=retry_result.error[:ERROR_TRUNCATE])
        self._abort_cherry_pick(ctx)
        ctx.save_report("failed", "cherry_pick_failed_after_merge_expert")
        return False

    def _log_conflict_files(self, ctx: IntegrationContext) -> None:
        ok, stdout, _, _ = run_git(self.workdir, ["git", "diff", "--name-only", "--diff-filter=U"])
        files = stdout.strip().splitlines() if ok else []
        ctx.step("conflict_files", files=files[:20])

    def _abort_cherry_pick(self, ctx: IntegrationContext) -> None:
        ok, _, stderr, _ = run_git(self.workdir, ["git", "cherry-pick", "--abort"])
        if ok:
            ctx.step("cherry_pick_aborted")
            return
        cherry_pick_head = Path(self.workdir) / ".git" / "CHERRY_PICK_HEAD"
        if cherry_pick_head.exists():
            ctx.step_error("cherry_pick_abort_failed", stderr=stderr[:ERROR_TRUNCATE])
            run_git(self.workdir, ["git", "reset", "--hard", "HEAD"])
            ctx.step("hard_reset_after_abort_failure")
