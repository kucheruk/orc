#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports for the git subsystem — the single runner abstraction used by
higher-level git operations. Allows tests to stub git without mocking
subprocess and keeps git-calling code inversion-of-control friendly.
"""

from __future__ import annotations

from typing import Protocol


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
