#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import signal
from pathlib import Path
from typing import Dict, Optional

import psutil

from ..io.logging import log_event

PROCESS_GROUP_TERM_TIMEOUT_SECONDS = 1.5


def is_posix() -> bool:
    return os.name == "posix"


def subprocess_group_spawn_kwargs() -> Dict[str, object]:
    """
    Spawn every agent in its own process group.

    This prevents cleanup of an agent monitor from accidentally sending SIGTERM
    to ORC itself when the child inherited ORC's PGID.
    """
    if is_posix():
        return {"start_new_session": True}
    return {}


def resolve_process_group_id(pid: Optional[int]) -> Optional[int]:
    if not pid or not is_posix():
        return None
    try:
        return os.getpgid(pid)
    except ProcessLookupError:
        return None
    except OSError:
        return None


def terminate_process_group(process_group_id: Optional[int], log_path: Path, label: str) -> bool:
    """
    Try to terminate all processes in a Unix process group.
    Returns True when this path is applicable on current platform.
    """
    if not process_group_id or not is_posix():
        return False

    group_members = [proc for proc in _group_processes(process_group_id) if int(getattr(proc, "pid", 0) or 0) > 0]
    pids = [proc.pid for proc in group_members]
    log_event(log_path, "INFO", "process group kill: terminate", label=label, pgid=process_group_id, pids=pids)
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        # Group already exited: idempotent success.
        return True
    except PermissionError:
        log_event(log_path, "WARN", "process group kill: terminate denied", label=label, pgid=process_group_id)
        return False
    except OSError as exc:
        log_event(log_path, "WARN", "process group kill: terminate failed", label=label, pgid=process_group_id, error=str(exc))
        return False

    _, alive = psutil.wait_procs(group_members, timeout=PROCESS_GROUP_TERM_TIMEOUT_SECONDS)
    if not alive:
        return True

    alive_pids = [proc.pid for proc in alive]
    log_event(log_path, "WARN", "process group kill: kill", label=label, pgid=process_group_id, pids=alive_pids)
    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        log_event(log_path, "WARN", "process group kill: kill denied", label=label, pgid=process_group_id)
        return False
    except OSError as exc:
        log_event(log_path, "WARN", "process group kill: kill failed", label=label, pgid=process_group_id, error=str(exc))
        return False

    _, still_alive = psutil.wait_procs(alive, timeout=PROCESS_GROUP_TERM_TIMEOUT_SECONDS)
    return not bool(still_alive)


def _group_processes(process_group_id: int) -> list[psutil.Process]:
    processes: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid"]):
        try:
            if os.getpgid(proc.pid) == process_group_id:
                processes.append(proc)
        except (ProcessLookupError, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        except (PermissionError, psutil.AccessDenied):
            # Best-effort collection: missing permissions should not fail cleanup.
            continue
        except OSError:
            continue
    return processes


def kill_own_process_group() -> None:
    """Send SIGTERM to our own process group. Best-effort, never raises."""
    try:
        os.killpg(os.getpgrp(), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
