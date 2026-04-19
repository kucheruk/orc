#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conflict resolution strategies for squash-merge integration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from ..errors.truncation import CONFLICT_ERROR_TRUNCATE, ERROR_TRUNCATE, REASON_TRUNCATE

if TYPE_CHECKING:
    from .integration_manager import IntegrationContext

from .git_helpers import run_git


class ConflictResolver:
    """Resolves merge conflicts via auto-resolve or merge expert."""

    def __init__(self, workdir: str) -> None:
        self.workdir = workdir

    def resolve(
        self,
        ctx: "IntegrationContext",
        initial_attempt,
        merge_expert_fn: Optional[Callable[[], bool]],
        abort_fn: Callable[["IntegrationContext"], None],
    ) -> bool:
        """Attempt to resolve a merge conflict.

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
        """Auto-resolve conflicts when ours/theirs are trivially reconcilable.

        Only handles cases where the result is unambiguous:
        - one side is empty (add-only from the other side);
        - both sides are identical (same change).

        For anything else (two divergent code changes to the same region),
        returns None so the caller falls through to the merge-expert agent.
        Never concatenates non-trivial code blocks — that tended to produce
        duplicate definitions / broken syntax and cost an entire pipeline
        round-trip to fix.

        Returns:
            True  — all conflicts resolved, commit succeeded
            False — attempted resolution but failed, merge aborted
            None  — not applicable, caller should try merge expert
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

        def _reconcile(match: "re.Match[str]") -> Optional[str]:
            ours, theirs = match.group(1), match.group(2)
            ours_stripped = ours.strip()
            theirs_stripped = theirs.strip()
            if not ours_stripped and not theirs_stripped:
                return ""
            if not ours_stripped:
                return theirs
            if not theirs_stripped:
                return ours
            if ours_stripped == theirs_stripped:
                return ours
            return None

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
            divergent = False
            def _sub(match: "re.Match[str]") -> str:
                nonlocal divergent
                resolution = _reconcile(match)
                if resolution is None:
                    divergent = True
                    return match.group(0)
                return resolution
            resolved = CONFLICT_RE.sub(_sub, text)
            if divergent or "<<<<<<< " in resolved:
                ctx.step("auto_resolve_skip", file=fpath, reason="divergent_conflict")
                return None
            try:
                full.write_text(resolved, encoding="utf-8")
            except OSError:
                abort_fn(ctx)
                ctx.save_report("failed", "auto_resolve_write_failed")
                return False

        for fpath in conflict_files:
            run_git(self.workdir, ["git", "add", "--", fpath])

        # For squash merge, commit directly (no cherry-pick --continue)
        ok_commit, _, stderr, _ = run_git(
            self.workdir,
            ["git", "commit", "--no-edit"],
        )
        if not ok_commit:
            # Fallback: try cherry-pick --continue for backward compat
            ok_commit, _, stderr, _ = run_git(
                self.workdir,
                ["git", "-c", "core.editor=true", "cherry-pick", "--continue"],
            )
        if ok_commit:
            ctx.step("auto_resolve_ok", files=conflict_files)
            ctx.save_report("completed", "merge_ok_after_auto_resolve")
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

        # Check for stale merge/cherry-pick state
        for marker in ("CHERRY_PICK_HEAD", "MERGE_HEAD"):
            marker_path = git_dir / marker
            if marker_path.exists():
                ctx.step_error(f"merge_expert_left_{marker.lower()}_in_progress")
                abort_fn(ctx)
                ctx.save_report("failed", f"merge_expert_did_not_complete_{marker.lower()}")
                return False

        # SQUASH_MSG without a commit means merge expert didn't commit
        squash_msg = git_dir / "SQUASH_MSG"
        if squash_msg.exists():
            # Try to commit — merge expert may have resolved but not committed
            ok_commit, _, _, _ = run_git(self.workdir, ["git", "commit", "--no-edit"])
            if not ok_commit:
                ctx.step_error("merge_expert_left_squash_uncommitted")
                abort_fn(ctx)
                ctx.save_report("failed", "merge_expert_did_not_commit_squash")
                return False

        ok, stdout, _, _ = run_git(self.workdir, ["git", "log", "--oneline", "-1"])
        ctx.step("merge_ok_after_merge_expert", head=stdout.strip()[:80])
        ctx.save_report("completed", "merge_ok_after_merge_expert")
        return True

    def _log_conflict_files(self, ctx: "IntegrationContext") -> None:
        ok, stdout, _, _ = run_git(self.workdir, ["git", "diff", "--name-only", "--diff-filter=U"])
        files = stdout.strip().splitlines() if ok else []
        ctx.step("conflict_files", files=files[:20])
