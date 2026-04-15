#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports for the git subsystem — the single runner abstraction used by
higher-level git operations. Allows tests to stub git without mocking
subprocess and keeps git-calling code inversion-of-control friendly.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol


class GitRunner(Protocol):
    """Runs one git command synchronously.

    Implementations return (ok, stdout, stderr, returncode). ``ok`` is
    True iff returncode == 0.
    """

    def run(
        self,
        workdir: str,
        args: list[str],
        *,
        timeout: float = 30.0,
    ) -> tuple[bool, str, str, int]: ...


class ConflictResolverPort(Protocol):
    """Resolves cherry-pick conflicts (auto-resolve trivial; merge-expert fallback)."""

    def resolve(
        self,
        ctx: Any,
        initial_attempt: Any,
        merge_expert_fn: Optional[Callable[[], bool]],
        abort_fn: Callable[[Any], None],
    ) -> bool: ...


class SafeFilesGuardPort(Protocol):
    """Saves/restores a curated set of tracked files across risky git operations."""

    def save(self) -> dict[str, str]: ...

    def restore(self, saved: dict[str, str]) -> None: ...

    def hard_reset_preserving(self) -> list[str]: ...
