#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from .atomic_io import write_json_atomic
from .logging import log_event
from .state_paths import tmp_dir

AGENT_LS_TIMEOUT_SECONDS = 15.0
TASK_RUNTIME_FILE_NAME = "orc-task-runtime.json"


def create_temp_backlog(workdir: str, task_text: str, log_path: Path) -> tuple[Path, str]:
    run_dir = tmp_dir(workdir)
    run_dir.mkdir(parents=True, exist_ok=True)
    task_id = "ORC-SMOKE-001"
    backlog_path = run_dir / f"BACKLOG.temp.{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    normalized = " ".join(task_text.strip().split())
    backlog_path.write_text(f"- [ ] {task_id} {normalized}\n", encoding="utf-8")
    rel_backlog = str(backlog_path.relative_to(Path(workdir)))
    log_event(log_path, "INFO", "temporary backlog created", backlog_path=str(backlog_path), task_id=task_id)
    return backlog_path, rel_backlog


def load_task_payload(task_path: Path) -> dict:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def runtime_state_path(task_path: Path) -> Path:
    return task_path.with_name(TASK_RUNTIME_FILE_NAME)


def load_runtime_payload(runtime_path: Path) -> dict:
    try:
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def init_runtime_payload(task_id: str) -> dict:
    return {
        "version": 1,
        "task_id": str(task_id or "").strip(),
        "active_seconds": 0.0,
        "last_heartbeat_at": 0.0,
        "run_id": "",
    }


def write_task_runtime_state(task_path: Path, task_id: str) -> Path:
    runtime_path = runtime_state_path(task_path)
    payload = init_runtime_payload(task_id)
    write_json_atomic(runtime_path, payload, ensure_ascii=False, indent=2)
    return runtime_path


def read_task_active_seconds(task_path: Path, expected_task_id: str = "") -> float:
    payload = load_runtime_payload(runtime_state_path(task_path))
    if not payload:
        return 0.0
    task_id = str(expected_task_id or "").strip()
    payload_task_id = str(payload.get("task_id") or "").strip()
    if task_id and payload_task_id and payload_task_id != task_id:
        return 0.0
    try:
        return max(float(payload.get("active_seconds") or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def delete_runtime_state_file(task_path: Path, log_path: Path, reason: str) -> bool:
    runtime_path = runtime_state_path(task_path)
    if not runtime_path.exists():
        return False
    try:
        runtime_path.unlink()
        log_event(log_path, "WARN", "runtime state file removed", reason=reason, runtime_path=str(runtime_path))
        return True
    except Exception as exc:
        log_event(
            log_path,
            "ERROR",
            "failed to remove runtime state file",
            reason=reason,
            error=str(exc),
            runtime_path=str(runtime_path),
        )
        return False


def delete_task_file(
    task_path: Path,
    log_path: Path,
    reason: str,
    expected_task_id: Optional[str] = None,
    expected_backlog: Optional[Path] = None,
) -> bool:
    if not task_path.exists():
        return False
    payload = load_task_payload(task_path)
    if expected_task_id and str(payload.get("task_id") or "").strip() != expected_task_id:
        log_event(
            log_path,
            "WARN",
            "skip task file remove: task_id mismatch",
            reason=reason,
            expected_task_id=expected_task_id,
            actual_task_id=str(payload.get("task_id") or ""),
        )
        return False
    if expected_backlog is not None:
        actual_backlog = str(payload.get("backlog_path") or "").strip()
        if actual_backlog and Path(actual_backlog) != expected_backlog:
            log_event(
                log_path,
                "WARN",
                "skip task file remove: backlog mismatch",
                reason=reason,
                expected_backlog=str(expected_backlog),
                actual_backlog=actual_backlog,
            )
            return False
    try:
        task_path.unlink()
        log_event(log_path, "WARN", "task file removed", reason=reason, task_path=str(task_path))
        delete_runtime_state_file(task_path, log_path, reason=f"{reason}:task_removed")
        return True
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to remove task file", reason=reason, error=str(exc), task_path=str(task_path))
        return False


def cleanup_stale_task_file(task_path: Path, log_path: Path, allowed_backlog: Optional[Path] = None) -> bool:
    if not task_path.exists():
        return False
    payload = load_task_payload(task_path)
    if not payload:
        return delete_task_file(task_path, log_path, reason="invalid_task_json")
    backlog_path_raw = str(payload.get("backlog_path") or "").strip()
    if not backlog_path_raw:
        return delete_task_file(task_path, log_path, reason="missing_backlog_path")
    backlog_path = Path(backlog_path_raw)
    if not backlog_path.exists():
        return delete_task_file(task_path, log_path, reason="backlog_missing")
    if allowed_backlog is not None and backlog_path.resolve() != allowed_backlog.resolve():
        log_event(
            log_path,
            "WARN",
            "task file references another backlog; keeping state",
            task_backlog=str(backlog_path),
            allowed_backlog=str(allowed_backlog),
        )
    return False


def update_task_conversation_id(task_path: Path, log_path: Path, conversation_id: str) -> None:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task file for conversation_id update", error=str(exc))
        return
    if payload.get("conversation_id") == conversation_id:
        return
    payload["conversation_id"] = conversation_id
    try:
        write_json_atomic(task_path, payload, ensure_ascii=False, indent=2)
        log_event(log_path, "INFO", "stored conversation_id from agent ls", conversation_id=conversation_id)
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to update conversation_id", error=str(exc))


def parse_agent_ls_output(output: str) -> Optional[str]:
    uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
    generic_re = re.compile(r"\b[A-Za-z0-9_-]{8,}\b")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        lower = line.lower()
        if lower.startswith(("id", "title", "name")):
            continue
        uuid_match = uuid_re.search(line)
        if uuid_match:
            return uuid_match.group(0)
        for token in generic_re.findall(line):
            token_lower = token.lower()
            if token_lower in {"id", "title", "name", "today", "yesterday"}:
                continue
            if ":" in token and all(part.isdigit() for part in token.split(":") if part):
                continue
            if not any(ch.isdigit() for ch in token):
                continue
            return token
    return None


def get_resume_id_from_agent_ls(workdir: str, log_path: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["agent", "ls"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=AGENT_LS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log_event(log_path, "ERROR", "agent ls timeout", timeout_seconds=AGENT_LS_TIMEOUT_SECONDS)
        return None
    except Exception as exc:
        log_event(log_path, "ERROR", "agent ls failed", error=str(exc))
        return None
    if result.returncode != 0:
        log_event(
            log_path,
            "ERROR",
            "agent ls returned non-zero",
            returncode=result.returncode,
            stderr=result.stderr[:500],
        )
        return None
    resume_id = parse_agent_ls_output(result.stdout)
    if resume_id:
        log_event(log_path, "INFO", "agent ls resume id", conversation_id=resume_id)
    else:
        log_event(log_path, "WARN", "agent ls returned no resume id")
    return resume_id
