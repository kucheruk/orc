#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from .backlog import is_task_done
from .logging import log_event


def create_temp_backlog(workdir: str, task_text: str, log_path: Path) -> tuple[Path, str]:
    run_dir = Path(workdir) / ".orc" / "tmp"
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
        task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
        )
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


def invoke_stop_hook_fallback(workdir: str, task_path: Path, log_path: Path) -> bool:
    stop_hook = Path(workdir) / ".cursor" / "hooks" / "orc_stop.py"
    if not stop_hook.exists():
        log_event(log_path, "WARN", "fallback stop skipped: hook missing", hook=str(stop_hook))
        return False
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "fallback stop: failed to read task file", error=str(exc))
        return False
    stdin_payload = {
        "status": "completed",
        "loop_count": 0,
        "conversation_id": payload.get("conversation_id") or "",
    }
    try:
        result = subprocess.run(
            ["python3", str(stop_hook)],
            cwd=workdir,
            input=json.dumps(stdin_payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "fallback stop: hook invocation failed", error=str(exc))
        return False
    log_event(
        log_path,
        "WARN" if result.returncode != 0 else "INFO",
        "fallback stop invoked",
        returncode=result.returncode,
        stdout=(result.stdout or "")[:500],
        stderr=(result.stderr or "")[:500],
    )
    return result.returncode == 0


def hard_cleanup_after_success(task_path: Path, log_path: Path) -> bool:
    payload = load_task_payload(task_path)
    backlog_path_raw = str(payload.get("backlog_path") or "").strip()
    current_task_id = str(payload.get("task_id") or "").strip()
    if not backlog_path_raw or not current_task_id:
        return False
    backlog_path = Path(backlog_path_raw)
    if not backlog_path.exists():
        return delete_task_file(
            task_path,
            log_path,
            reason="result_success_backlog_missing",
            expected_task_id=current_task_id,
        )
    if is_task_done(backlog_path, current_task_id):
        return delete_task_file(
            task_path,
            log_path,
            reason="result_success_backlog_already_done",
            expected_task_id=current_task_id,
            expected_backlog=backlog_path,
        )
    return False
