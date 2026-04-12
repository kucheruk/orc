#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import psutil

from ..io.atomic_io import write_json_atomic
from ..io.logging import log_event, now_iso

ORPHAN_SWEEP_COMMAND_MARKERS = (
    "agent",
    "orc.py",
    "pytest",
    "unittest",
    "pyenv-which",
    "orc_stop.py",
    "orc_before_submit.py",
)


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def load_lockfile(lock_path: Path) -> Dict[str, object]:
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def acquire_lock(lock_path: Path, log_path: Path) -> None:
    if lock_path.exists():
        data = load_lockfile(lock_path)
        lock_pid = int(data.get("pid") or 0)
        if lock_pid and is_pid_alive(lock_pid):
            log_event(log_path, "ERROR", "lockfile: active orchestrator detected", pid=lock_pid)
            print("Another orchestrator instance is running.", file=sys.stderr)
            raise SystemExit(3)
        # Kill entire stale process group if PGID was recorded
        stale_pgid = int(data.get("pgid") or 0)
        if stale_pgid:
            try:
                os.killpg(stale_pgid, signal.SIGKILL)
                log_event(log_path, "WARN", "lockfile: killed stale process group", pgid=stale_pgid)
            except (ProcessLookupError, PermissionError, OSError):
                pass
        log_event(log_path, "WARN", "lockfile: stale lock removed", stale_pid=lock_pid)
        try:
            lock_path.unlink()
        except Exception as exc:
            log_event(log_path, "ERROR", "lockfile: failed to remove stale lock", error=str(exc))
    payload = {"pid": os.getpid(), "pgid": os.getpgrp(), "started_at": now_iso()}
    write_json_atomic(lock_path, payload, ensure_ascii=False, indent=2)
    log_event(log_path, "INFO", "lockfile: acquired", pid=os.getpid())


def release_lock(lock_path: Path, log_path: Path) -> None:
    try:
        if lock_path.exists():
            lock_path.unlink()
            log_event(log_path, "INFO", "lockfile: released")
    except Exception as exc:
        log_event(log_path, "ERROR", "lockfile: failed to release", error=str(exc))


def list_child_pids(pid: int) -> List[int]:
    try:
        process = psutil.Process(pid)
        children = process.children(recursive=False)
    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied, ValueError):
        return []
    return [child.pid for child in children]


def build_process_tree(root_pid: int) -> List[int]:
    tree: List[int] = []
    queue = [root_pid]
    seen = set()
    while queue:
        pid = queue.pop(0)
        if pid in seen:
            continue
        seen.add(pid)
        tree.append(pid)
        children = list_child_pids(pid)
        for child in children:
            if child not in seen:
                queue.append(child)
    return tree


def kill_process_tree(root_pid: Optional[int], log_path: Path, label: str) -> None:
    if not root_pid:
        log_event(log_path, "WARN", "process tree kill skipped: no pid", label=label)
        return
    try:
        parent = psutil.Process(root_pid)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return
    except psutil.AccessDenied:
        log_event(log_path, "WARN", "process tree kill skipped: access denied", label=label, pid=root_pid)
        return

    try:
        children = parent.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        children = []
    except psutil.AccessDenied:
        log_event(log_path, "WARN", "process tree kill: cannot enumerate children", label=label, pid=root_pid)
        children = []

    pids = [proc.pid for proc in children] + [root_pid]
    log_event(log_path, "INFO", "process tree kill: terminate", label=label, pids=pids)

    for child in children:
        try:
            child.terminate()
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        except psutil.AccessDenied:
            log_event(log_path, "WARN", "process tree kill: terminate denied", label=label, pid=child.pid)

    _, alive_children = psutil.wait_procs(children, timeout=1.5)
    if alive_children:
        alive_pids = [proc.pid for proc in alive_children]
        log_event(log_path, "WARN", "process tree kill: kill", label=label, pids=alive_pids)
        for child in alive_children:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied:
                log_event(log_path, "WARN", "process tree kill: kill denied", label=label, pid=child.pid)

    try:
        parent.terminate()
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return
    except psutil.AccessDenied:
        log_event(log_path, "WARN", "process tree kill: terminate denied", label=label, pid=root_pid)
        return

    _, alive_parent = psutil.wait_procs([parent], timeout=1.5)
    if alive_parent:
        try:
            parent.kill()
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return
        except psutil.AccessDenied:
            log_event(log_path, "WARN", "process tree kill: kill denied", label=label, pid=root_pid)


def kill_orphan_project_processes(
    workdir: str,
    log_path: Path,
    label: str,
    *,
    started_after: Optional[float] = None,
    command_markers: Optional[Sequence[str]] = None,
    run_token: Optional[str] = None,
) -> list[int]:
    """
    Best-effort sweep for detached orphan processes related to the workspace.
    Targets only orphaned processes (PPID=1) with cwd/cmdline tied to workdir.
    """
    workspace = str(workdir or "").strip()
    if not workspace:
        return []
    try:
        workspace_path_obj = Path(workspace).resolve()
    except Exception:
        workspace_path_obj = Path(workspace)
    workspace_path = str(workspace_path_obj)
    markers = [str(marker).strip().lower() for marker in (command_markers or ()) if str(marker).strip()]
    token = str(run_token or "").strip()

    threshold = None
    if isinstance(started_after, (int, float)):
        threshold = float(started_after) - 2.0

    def _same_or_subpath(candidate: str) -> bool:
        raw = str(candidate or "").strip()
        if not raw:
            return False
        if not os.path.isabs(raw):
            return False
        try:
            path_obj = Path(raw).resolve()
        except Exception:
            path_obj = Path(raw)
        return path_obj == workspace_path_obj or workspace_path_obj in path_obj.parents

    matched: list[Tuple[psutil.Process, str, str, str]] = []
    for proc in psutil.process_iter(["pid", "ppid", "cmdline", "cwd", "create_time", "name"]):
        try:
            if proc.pid == os.getpid():
                continue
            info = proc.info
            if int(info.get("ppid") or 0) != 1:
                continue
            if threshold is not None:
                created = float(info.get("create_time") or 0.0)
                if created and created < threshold:
                    continue

            cmdline = info.get("cmdline") or []
            cmd_text = " ".join(str(part) for part in cmdline if part).lower()
            proc_name = str(info.get("name") or "").lower()
            cwd_raw = str(info.get("cwd") or "").strip()
            matched_by = ""
            if token:
                try:
                    env = proc.environ()
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    env = {}
                if str(env.get("ORC_RUN_TOKEN") or "").strip() == token:
                    matched_by = "token"

            if not matched_by:
                in_workspace = _same_or_subpath(cwd_raw) or any(
                    _same_or_subpath(part) for part in cmdline if isinstance(part, str)
                )
                if not in_workspace:
                    continue
                if markers:
                    if not any(marker in cmd_text or marker in proc_name for marker in markers):
                        continue
                    matched_by = "marker"
                else:
                    matched_by = "workspace"
            matched.append((proc, matched_by, cwd_raw, cmd_text[:300]))
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied, ValueError):
            continue

    if not matched:
        return []

    pids = [proc.pid for proc, _, _, _ in matched]
    matches = [
        {"pid": proc.pid, "matched_by": matched_by, "cwd": cwd, "cmdline": cmd}
        for proc, matched_by, cwd, cmd in matched
    ]
    log_event(log_path, "WARN", "orphan sweep: terminate", label=label, workspace=workspace_path, pids=pids, matches=matches)
    for proc, _, _, _ in matched:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        except psutil.AccessDenied:
            log_event(log_path, "WARN", "orphan sweep: terminate denied", label=label, pid=proc.pid)

    processes = [proc for proc, _, _, _ in matched]
    _, alive = psutil.wait_procs(processes, timeout=1.0)
    if alive:
        alive_pids = [proc.pid for proc in alive]
        log_event(log_path, "WARN", "orphan sweep: kill", label=label, pids=alive_pids)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied:
                log_event(log_path, "WARN", "orphan sweep: kill denied", label=label, pid=proc.pid)
        time.sleep(0.05)
    return pids
