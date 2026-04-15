#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concrete adapter for tasks.ports.StatePathsPort — FS-backed implementation.

Tonkik facade over module-level helpers in state_paths.py so that business code
can depend on the port instead of importing path functions directly.
"""
from __future__ import annotations

from pathlib import Path

from .state_paths import (
    active_task_path,
    run_root,
    stats_path,
    tmp_dir,
)


class FsStatePaths:
    """Default StatePathsPort implementation backed by state_paths.py helpers."""

    def active_task(self, workdir: str) -> Path:
        return active_task_path(workdir)

    def tmp_dir(self, workdir: str) -> Path:
        return tmp_dir(workdir)

    def stats(self, workdir: str) -> Path:
        return stats_path(workdir)

    def run_root(self, workdir: str, name: str = "backlog-run") -> Path:
        return run_root(workdir, name)


DEFAULT_STATE_PATHS = FsStatePaths()
