#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subprocess git probes used by hook scripts.

Kept separate from `hook_io` so the subprocess dependency is explicit and
isolated. Timeouts live with `orc_core.git.subprocess_git` (git package,
not board/tasks/agents — allowed boundary).
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from orc_core.git.subprocess_git import GIT_COMMAND_TIMEOUT_SECONDS

from .hook_io import log_event


def git_has_changes(repo_root: Path, log_path: Optional[Path] = None) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        if log_path:
            log_event(log_path, "ERROR", "git status timeout", timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS)
        return True
    except Exception as exc:
        if log_path:
            log_event(log_path, "ERROR", "git status failed", error=str(exc))
        return True
    if result.returncode != 0:
        if log_path:
            log_event(
                log_path,
                "ERROR",
                "git status non-zero",
                returncode=result.returncode,
                stderr=result.stderr[:500],
            )
        return True
    return bool(result.stdout.strip())


def git_has_recent_commit(repo_root: Path, since_iso: str, log_path: Optional[Path] = None) -> bool:
    if not since_iso:
        return False
    normalized = str(since_iso).strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        since_dt = datetime.fromisoformat(normalized)
    except Exception as exc:
        if log_path:
            log_event(log_path, "ERROR", "invalid created_at for recent commit check", value=since_iso, error=str(exc))
        return False
    local_tz = datetime.now().astimezone().tzinfo or timezone.utc
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=local_tz)
    try:
        result = subprocess.run(
            ["git", "log", "-n", "1", "--pretty=%ct"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        if log_path:
            log_event(log_path, "ERROR", "git log timeout", timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS)
        return False
    except Exception as exc:
        if log_path:
            log_event(log_path, "ERROR", "git log failed", error=str(exc))
        return False
    if result.returncode != 0:
        if log_path:
            log_event(
                log_path,
                "ERROR",
                "git log non-zero",
                returncode=result.returncode,
                stderr=result.stderr[:500],
            )
        return False
    raw_ts = str(result.stdout or "").strip()
    if not raw_ts:
        return False
    try:
        commit_ts = int(raw_ts)
    except Exception as exc:
        if log_path:
            log_event(log_path, "ERROR", "git log timestamp parse failed", raw=raw_ts[:120], error=str(exc))
        return False
    return commit_ts >= int(since_dt.timestamp())
