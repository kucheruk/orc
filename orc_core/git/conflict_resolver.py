#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conflict resolution strategies for cherry-pick integration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from ..models.session_types import CONFLICT_ERROR_TRUNCATE, ERROR_TRUNCATE, REASON_TRUNCATE

if TYPE_CHECKING:
    from .integration_manager import IntegrationContext

from .worktree_flow import run_git


class ConflictResolver:
    """Resolves cherry-pick conflicts via auto-resolve or merge expert."""

    def __init__(self, workdir: str) -> None:
        self.workdir = workdir

    def resolve(
        self,
        ctx: "IntegrationContext",
        initial_attempt,
        merge_expert_fn: Optional[Callable[[], bool]],
        abort_fn: Callable[["IntegrationContext"], None],
    ) -> bool:
        """Attempt to resolve a cherry-pick conflict.

        Tries auto-resolve first, then falls back to merge expert.
        Returns True if conflict was resolved successfully.
        """
        ctx.step("conflict_detected", error=initial_attempt.error[:CONFLICT_ERROR_TRUNCATE])
        self._log_conflict_files(ctx)

        auto_result = self._try_auto_resolve(ctx, abort_fn)
        if auto_result is True:
            return True
        if auto_result is False:
            return False

        # auto_result is None: auto-resolve not applicable, try merge expert
        if not self._invoke_merge_expert(ctx, merge_expert_fn, abort_fn):
            return False

        return self._verify_merge_expert_result(ctx, abort_fn)

    def _try_auto_resolve(
        self,
        ctx: "IntegrationContext",
        abort_fn: Callable[["IntegrationContext"], None],
    ) -> Optional[bool]:
        """Auto-resolve trivial conflicts by keeping both sides (ours + theirs).

        Returns:
            True  — all conflicts resolved, cherry-pick committed
            False — attempted resolution but failed, cherry-pick aborted
            None  — not applicable (complex conflicts), caller should try merge expert
        """
        ok, stdout, _, _ = run_git(self.workdir, ["git", "diff", "--name-only", "--diff-filter=U"])
        if not ok:
            return None
        conflict_files = [f for f in stdout.strip().splitlines() if f.strip()]
        if not conflict_files:
            return None

        CONFLICT_RE = re.compile(
            r"<<<<<<<[^\n]*\r?\n(.*?)=======\r?\n(.*?)>>>>>>>[^\n]*\r?\n",
            re.DOTALL,
        )

        for fpath in conflict_files:
            full = Path(self.workdir) / fpath
            if not full.exists():
                ctx.step("auto_resolve_skip", file=fpath, reason="file_not_found")
                return None
            try:
                text = full.read_text(encoding="utf-8")
            except OSError:
                return None
            if "<<<<<<< " not in text:
                continue
            resolved = CONFLICT_RE.sub(r"\1\2", text)
            if "<<<<<<< " in resolved:
                ctx.step("auto_resolve_skip", file=fpath, reason="complex_conflict")
                return None
            try:
                full.write_text(resolved, encoding="utf-8")
            except OSError:
                abort_fn(ctx)
                ctx.save_report("failed", "auto_resolve_write_failed")
                return False

        for fpath in conflict_files:
            run_git(self.workdir, ["git", "add", fpath])

        ok_commit, _, stderr, _ = run_git(
            self.workdir,
            ["git", "-c", "core.editor=true", "cherry-pick", "--continue"],
        )
        if ok_commit:
            ctx.step("auto_resolve_ok", files=conflict_files)
            ctx.save_report("completed", "cherry_pick_ok_after_auto_resolve")
            return True

        ctx.step("auto_resolve_failed", stderr=stderr[:ERROR_TRUNCATE])
        abort_fn(ctx)
        ctx.save_report("failed", "auto_resolve_continue_failed")
        return False

    def _invoke_merge_expert(
        self,
        ctx: "IntegrationContext",
        merge_expert_fn: Optional[Callable[[], bool]],
        abort_fn: Callable[["IntegrationContext"], None],
    ) -> bool:
        if not merge_expert_fn:
            ctx.step_error("no_merge_expert_available")
            abort_fn(ctx)
            ctx.save_report("failed", "no_merge_expert")
            return False

        ctx.step("merge_expert_start")
        if not merge_expert_fn():
            ctx.step_error("merge_expert_failed")
            abort_fn(ctx)
            ctx.save_report("failed", "merge_expert_failed")
            return False

        ctx.step("merge_expert_completed")
        return True

    def _verify_merge_expert_result(
        self,
        ctx: "IntegrationContext",
        abort_fn: Callable[["IntegrationContext"], None],
    ) -> bool:
        ctx.step("verify_after_merge_expert")
        ok, out, _, _ = run_git(self.workdir, ["git", "rev-parse", "--git-dir"])
        git_dir = Path(out.strip()) if ok else Path(self.workdir) / ".git"
        if not git_dir.is_absolute():
            git_dir = Path(self.workdir) / git_dir

        cherry_pick_head = git_dir / "CHERRY_PICK_HEAD"
        if cherry_pick_head.exists():
            ctx.step_error("merge_expert_left_cherry_pick_in_progress")
            abort_fn(ctx)
            ctx.save_report("failed", "merge_expert_did_not_complete_cherry_pick")
            return False

        ok, stdout, _, _ = run_git(self.workdir, ["git", "log", "--oneline", "-1"])
        ctx.step("cherry_pick_ok_after_merge_expert", head=stdout.strip()[:80])
        ctx.save_report("completed", "cherry_pick_ok_after_merge_expert")
        return True

    def _log_conflict_files(self, ctx: "IntegrationContext") -> None:
        ok, stdout, _, _ = run_git(self.workdir, ["git", "diff", "--name-only", "--diff-filter=U"])
        files = stdout.strip().splitlines() if ok else []
        ctx.step("conflict_files", files=files[:20])
