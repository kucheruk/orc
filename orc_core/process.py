#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .logging import log_event, now_iso


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
        log_event(log_path, "WARN", "lockfile: stale lock removed", stale_pid=lock_pid)
        try:
            lock_path.unlink()
        except Exception as exc:
            log_event(log_path, "ERROR", "lockfile: failed to remove stale lock", error=str(exc))
    payload = {"pid": os.getpid(), "started_at": now_iso()}
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
        result = subprocess.run(
            ["pgrep", "-P", str(pid)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    pids = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return pids


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
    pids = build_process_tree(root_pid)
    log_event(log_path, "INFO", "process tree kill: SIGTERM", label=label, pids=pids)
    for pid in reversed(pids):
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            continue
    time.sleep(1.5)
    still_alive = [pid for pid in pids if is_pid_alive(pid)]
    if still_alive:
        log_event(log_path, "WARN", "process tree kill: SIGKILL", label=label, pids=still_alive)
        for pid in reversed(still_alive):
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                continue
