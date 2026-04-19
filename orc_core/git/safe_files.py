#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protects a curated set of tracked files across git operations that would otherwise
overwrite them (cherry-pick, hard reset). Saves contents before, restores after."""

from __future__ import annotations

import logging
from pathlib import Path

from ..log import log_event
from ..errors.truncation import ERROR_TRUNCATE
from .git_helpers import run_git

_logger = logging.getLogger(__name__)


class SafeFilesGuard:
    """Saves and restores a set of tracked file paths across risky git operations.

    Used by IntegrationManager to shield specific paths from cherry-pick
    overwrites and from ``git reset --hard`` during stale-state recovery.
    """

    def __init__(
        self,
        workdir: str,
        safe_tracked_paths: frozenset[str],
        *,
        log_path: Path,
    ) -> None:
        self._workdir = workdir
        self._safe_tracked_paths = safe_tracked_paths
        self._log_path = log_path

    def save(self) -> dict[str, str]:
        """Read safe files from disk, checkout -- them, return captured contents."""
        saved: dict[str, str] = {}
        for safe_path in self._safe_tracked_paths:
            full = Path(self._workdir) / safe_path
            if not full.exists():
                continue
            try:
                saved[safe_path] = full.read_text(encoding="utf-8")
            except OSError:
                continue
            run_git(self._workdir, ["git", "checkout", "--", safe_path])
        return saved

    def restore(self, saved: dict[str, str]) -> None:
        """Write captured contents back onto disk."""
        for safe_path, content in saved.items():
            full = Path(self._workdir) / safe_path
            try:
                full.write_text(content, encoding="utf-8")
            except OSError:
                _logger.debug("OSError on safe path I/O", exc_info=True)

    def hard_reset_preserving(self) -> list[str]:
        """Read safe files, ``git reset --hard HEAD``, then write them back."""
        saved: dict[str, str] = {}
        for safe_path in self._safe_tracked_paths:
            full = Path(self._workdir) / safe_path
            if full.exists():
                try:
                    saved[safe_path] = full.read_text(encoding="utf-8")
                except OSError:
                    _logger.debug("OSError reading safe path", exc_info=True)
        ok, _, stderr, _ = run_git(self._workdir, ["git", "reset", "--hard", "HEAD"])
        if not ok:
            raise RuntimeError(f"git reset --hard HEAD failed: {stderr.strip()[:ERROR_TRUNCATE]}")
        for safe_path, content in saved.items():
            full = Path(self._workdir) / safe_path
            try:
                full.write_text(content, encoding="utf-8")
            except OSError:
                _logger.debug("OSError on safe path I/O", exc_info=True)
        preserved = list(saved.keys())
        log_event(self._log_path, "WARN", "hard reset with preserved files",
                  preserved=preserved)
        return preserved
