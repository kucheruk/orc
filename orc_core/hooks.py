#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Tuple

from .backlog import Task
from .logging import log_event, now_iso


def ensure_repo_hooks(workdir: str) -> Tuple[Path, Path]:
    hooks_dir = Path(workdir) / ".orc" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    before_path = hooks_dir / "orc_before_submit.py"
    stop_path = hooks_dir / "orc_stop.py"
    hook_lib_path = hooks_dir / "orc_hook_lib.py"

    orc_root = Path(__file__).resolve().parents[1]
    hook_lib_script = """#!/usr/bin/env python3
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

ORC_ROOT = Path(__ORC_ROOT__)
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"

TASK_RE = re.compile(
    r"^(?P<prefix>\\s*[-*]\\s*\\[)(?P<mark>[ xX])(?P<suffix>\\]\\s+)(?P<text>.+?)\\s*$"
)
TASK_ID_RE = re.compile(r"(?:\\*\\*)?(?P<id>[A-Z][A-Z0-9_-]+)(?::)?(?:\\*\\*)?\\s", re.UNICODE)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def log_event(path: Path, level: str, message: str, **fields):
    min_level = LOG_LEVELS.get(os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip(), LOG_LEVELS[DEFAULT_LOG_LEVEL])
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": now_iso(), "level": level, "message": message, **fields}
    with path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(json.dumps(payload, ensure_ascii=False) + "\\n")

def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def git_has_changes(repo_root: Path, log_path: Optional[Path] = None) -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
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

def extract_task_id(text: str):
    m = TASK_ID_RE.search(text)
    return m.group("id") if m else None

def is_task_marked(path: Path, task_id: str) -> bool:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        m = TASK_RE.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        if extract_task_id(text) != task_id:
            continue
        return m.group("mark").lower() == "x"
    return False

def mark_task_done(path: Path, task_id: str) -> bool:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        m = TASK_RE.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        if extract_task_id(text) != task_id:
            continue
        if m.group("mark").lower() == "x":
            return True
        lines[i] = f"{m.group('prefix')}x{m.group('suffix')}{m.group('text')}"
        path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        return True
    return False

def parse_backlog_counts(path: Path) -> Tuple[int, int]:
    total = 0
    done = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = TASK_RE.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        if not extract_task_id(text):
            continue
        total += 1
        if m.group("mark").lower() == "x":
            done += 1
    return total, done

def _load_telegram_config(log_path: Path) -> dict:
    config_path = ORC_ROOT / ".orc" / "telegram.json"
    if not config_path.exists():
        log_event(log_path, "ERROR", "telegram config missing", path=str(config_path))
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "telegram config invalid", error=str(exc), path=str(config_path))
        return {}

def _resolve_telegram_credentials(log_path: Path) -> tuple[str, str]:
    env_token = os.environ.get("ORC_TELEGRAM_TOKEN", "").strip()
    env_chat_id = os.environ.get("ORC_TELEGRAM_CHAT_ID", "").strip()
    if env_token and env_chat_id:
        return env_token, env_chat_id
    cfg = _load_telegram_config(log_path)
    token = str(cfg.get("token") or "").strip()
    chat_id = str(cfg.get("chat_id") or "").strip()
    return token, chat_id

def _truncate_message(message: str, max_len: int = 3800) -> tuple[str, bool]:
    if len(message) <= max_len:
        return message, False
    suffix = "\\n...(truncated)"
    cutoff = max_len - len(suffix)
    if cutoff <= 0:
        return suffix.strip(), True
    return message[:cutoff] + suffix, True

def send_telegram_message(message: str, log_path: Path) -> None:
    token, chat_id = _resolve_telegram_credentials(log_path)
    if not token or not chat_id:
        log_event(log_path, "ERROR", "telegram credentials missing")
        return
    log_event(log_path, "INFO", "telegram send requested", text=message)
    message, truncated = _truncate_message(message)
    if truncated:
        log_event(log_path, "WARN", "telegram message truncated", max_len=3800)
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(api_url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except Exception as exc:
        log_event(log_path, "ERROR", "telegram send failed", error=str(exc))
        return
    if not data.get("ok"):
        log_event(log_path, "ERROR", "telegram send error", response=data, raw=raw[:500])
        return
    log_event(log_path, "INFO", "telegram sent", response=data)

def load_stats(repo_root: Path) -> Dict[str, object]:
    stats_path = repo_root / ".orc" / "orc-stats.json"
    data = read_json(stats_path, {})
    data.setdefault("created_at", now_iso())
    data.setdefault("started_at", data.get("started_at") or "")
    data.setdefault("tokens_total", int(data.get("tokens_total") or 0))
    data.setdefault("tokens_by_task", data.get("tokens_by_task") or {})
    return data

def save_stats(repo_root: Path, stats: Dict[str, object]) -> None:
    stats_path = repo_root / ".orc" / "orc-stats.json"
    write_json(stats_path, stats)

def ensure_started(stats: Dict[str, object], done_tasks: int) -> Dict[str, object]:
    if not stats.get("started_at"):
        stats["started_at"] = now_iso()
        stats["start_done"] = int(done_tasks)
    if "start_done" not in stats:
        stats["start_done"] = int(done_tasks)
    else:
        stats["start_done"] = int(stats.get("start_done") or 0)
    return stats

def read_task_tokens(repo_root: Path) -> Optional[int]:
    metrics_path = repo_root / ".orc" / "orc-metrics.json"
    data = read_json(metrics_path, {})
    tokens = data.get("tokens_total")
    if isinstance(tokens, (int, float)):
        return int(tokens)
    return None

def update_tokens(stats: Dict[str, object], task_id: str, task_tokens: Optional[int]) -> Dict[str, object]:
    if task_tokens is None:
        return stats
    tokens_by_task = stats.setdefault("tokens_by_task", {})
    if task_id and str(task_id) in tokens_by_task:
        return stats
    if task_id:
        tokens_by_task[str(task_id)] = int(task_tokens)
    stats["tokens_total"] = int(stats.get("tokens_total") or 0) + int(task_tokens)
    return stats

def format_duration(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def build_report(stats: Dict[str, object], total_tasks: int, done_tasks: int) -> Dict[str, object]:
    stats = ensure_started(stats, done_tasks)
    started_at = stats.get("started_at") or now_iso()
    try:
        started = datetime.fromisoformat(str(started_at))
    except ValueError:
        started = datetime.now()
        stats["started_at"] = started.isoformat(timespec="seconds")
    now = datetime.now()
    elapsed = max((now - started).total_seconds(), 0.0)
    minutes = max(elapsed / 60.0, 0.001)
    hours = max(elapsed / 3600.0, 0.001)
    tokens_total = int(stats.get("tokens_total") or 0)
    tokens_per_min = tokens_total / minutes
    start_done = int(stats.get("start_done") or 0)
    completed_since_start = max(done_tasks - start_done, 0)
    tasks_per_hour = (completed_since_start / hours) if completed_since_start else 0.0
    remaining = max(total_tasks - done_tasks, 0)
    eta = "unknown"
    if tasks_per_hour > 0:
        eta = format_duration((remaining / tasks_per_hour) * 3600.0)
    return {
        "running_time": format_duration(elapsed),
        "tokens_total": tokens_total,
        "tokens_per_min": tokens_per_min,
        "tasks_per_hour": tasks_per_hour,
        "eta": eta,
        "tasks_remaining": remaining,
    }

def format_report(report: Dict[str, object]) -> str:
    return "\\n".join(
        [
            f"running_time={report['running_time']}",
            f"tokens_total={report['tokens_total']}",
            f"tokens_per_min={report['tokens_per_min']:.1f}",
            f"tasks_per_hour={report['tasks_per_hour']:.2f}",
            f"eta={report['eta']}",
            f"tasks_remaining={report['tasks_remaining']}",
        ]
    )
"""
    hook_lib_script = hook_lib_script.replace("__ORC_ROOT__", repr(str(orc_root)))

    before_script = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import orc_hook_lib as lib

def main() -> int:
    script_repo = Path(__file__).resolve().parents[2]
    orc_dir = script_repo / ".orc"
    cursor_dir = script_repo / ".cursor"
    log_path = orc_dir / "orc-hook.log"
    try:
        raw = sys.stdin.read() or "{}"
        data = json.loads(raw)
    except Exception as exc:
        lib.log_event(log_path, "ERROR", "beforeSubmitPrompt: bad input", error=str(exc))
        data = {}

    roots = data.get("workspace_roots") or []
    if roots and str(script_repo) not in roots:
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: workspace mismatch", roots=roots)
        return 0

    task_file = orc_dir / "orc-task.json"
    if not task_file.exists():
        cursor_task_file = cursor_dir / "orc-task.json"
        if cursor_task_file.exists():
            task_file = cursor_task_file
    lib.log_event(log_path, "INFO", "beforeSubmitPrompt", conversation_id=data.get("conversation_id"))
    if not task_file.exists():
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: no task file")
        return 0

    task = lib.read_json(task_file, {})
    conv_id = data.get("conversation_id")
    if conv_id and not task.get("conversation_id"):
        task["conversation_id"] = conv_id
        lib.write_json(task_file, task)
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: stored conversation_id", conversation_id=conv_id)
    else:
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: conversation_id unchanged")

    if not task.get("start_notified"):
        backlog_path = task.get("backlog_path")
        task_id = task.get("task_id") or ""
        task_text = task.get("task_text") or ""
        total, done = (0, 0)
        if backlog_path:
            try:
                total, done = lib.parse_backlog_counts(Path(backlog_path))
            except Exception as exc:
                lib.log_event(log_path, "ERROR", "start: backlog parse failed", error=str(exc))
        stats = lib.load_stats(script_repo)
        stats = lib.ensure_started(stats, done)
        report = lib.build_report(stats, total, done)
        report_text = lib.format_report(report)
        message = f"**Старт задачи**\\n{task_id} — {task_text}\\n\\n{report_text}"
        lib.log_event(log_path, "INFO", "start: message prepared", task_id=task_id, text=message)
        lib.send_telegram_message(message, log_path)
        task["start_notified"] = True
        lib.write_json(task_file, task)
        lib.save_stats(script_repo, stats)
        lib.log_event(log_path, "INFO", "start: notified", task_id=task_id)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""

    stop_script = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import orc_hook_lib as lib

def main() -> int:
    script_repo = Path(__file__).resolve().parents[2]
    orc_dir = script_repo / ".orc"
    cursor_dir = script_repo / ".cursor"
    log_path = orc_dir / "orc-hook.log"
    try:
        raw = sys.stdin.read() or "{}"
        data = json.loads(raw)
    except Exception as exc:
        lib.log_event(log_path, "ERROR", "stop: bad input", error=str(exc))
        data = {}

    roots = data.get("workspace_roots") or []
    if roots and str(script_repo) not in roots:
        lib.log_event(log_path, "INFO", "stop: workspace mismatch", roots=roots)
        return 0

    task_file = orc_dir / "orc-task.json"
    if not task_file.exists():
        cursor_task_file = cursor_dir / "orc-task.json"
        if cursor_task_file.exists():
            task_file = cursor_task_file
    lib.log_event(
        log_path,
        "INFO",
        "stop",
        status=data.get("status"),
        loop_count=data.get("loop_count"),
        conversation_id=data.get("conversation_id"),
    )
    if not task_file.exists():
        lib.log_event(log_path, "INFO", "stop: no task file")
        return 0

    task = lib.read_json(task_file, {})
    if not task:
        lib.log_event(log_path, "ERROR", "stop: bad task file")
        return 0

    conv_id = data.get("conversation_id")
    if task.get("conversation_id") and conv_id and task["conversation_id"] != conv_id:
        lib.log_event(
            log_path,
            "WARN",
            "stop: conversation_id mismatch (continuing)",
            task_conversation_id=task.get("conversation_id"),
            got_conversation_id=conv_id,
        )

    backlog_path = task.get("backlog_path")
    task_id = task.get("task_id")
    if not backlog_path or not task_id:
        lib.log_event(log_path, "ERROR", "stop: missing backlog_path/task_id")
        return 0
    status = data.get("status")
    already_done = False
    if status != "completed":
        try:
            already_done = lib.is_task_marked(Path(backlog_path), task_id)
        except Exception as exc:
            lib.log_event(log_path, "ERROR", "stop: failed to read backlog", error=str(exc))
            already_done = False
        if not already_done:
            lib.log_event(log_path, "INFO", "stop: status not completed")
            return 0
        lib.log_event(log_path, "WARN", "stop: status not completed but task already marked", task_id=task_id, status=status)

    if status == "completed" and not lib.git_has_changes(script_repo, log_path):
        lib.log_event(log_path, "WARN", "stop: no git changes; retrying task", task_id=task_id)
        try:
            task_file.unlink()
        except Exception as exc:
            lib.log_event(log_path, "ERROR", "stop: failed to delete task file", error=str(exc))
        other_task_file = cursor_dir / "orc-task.json" if task_file.parent.name != ".cursor" else orc_dir / "orc-task.json"
        if other_task_file.exists():
            try:
                other_task_file.unlink()
            except Exception as exc:
                lib.log_event(log_path, "ERROR", "stop: failed to delete mirrored task file", error=str(exc))
        return 0

    if lib.mark_task_done(Path(backlog_path), task_id):
        lib.log_event(log_path, "INFO", "stop: marked task", task_id=task_id)
        try:
            task_file.unlink()
        except Exception as exc:
            lib.log_event(log_path, "ERROR", "stop: failed to delete task file", error=str(exc))
        other_task_file = cursor_dir / "orc-task.json" if task_file.parent.name != ".cursor" else orc_dir / "orc-task.json"
        if other_task_file.exists():
            try:
                other_task_file.unlink()
            except Exception as exc:
                lib.log_event(log_path, "ERROR", "stop: failed to delete mirrored task file", error=str(exc))
        loop_count = int(data.get("loop_count") or 0)
        task_text = str(task.get("task_text") or "").strip()
        task_notes_path = script_repo / "tasks" / f"{task_id}.md"
        task_notes = ""
        if task_notes_path.exists():
            try:
                task_notes = task_notes_path.read_text(encoding="utf-8").strip()
            except Exception as exc:
                lib.log_event(log_path, "ERROR", "stop: failed to read task notes", error=str(exc))
                task_notes = ""
        if task_notes:
            task_text = task_notes
        total, done = (0, 0)
        try:
            total, done = lib.parse_backlog_counts(Path(backlog_path))
        except Exception as exc:
            lib.log_event(log_path, "ERROR", "stop: backlog parse failed", error=str(exc))
        stats = lib.load_stats(script_repo)
        task_tokens = lib.read_task_tokens(script_repo)
        stats = lib.update_tokens(stats, task_id, task_tokens)
        report = lib.build_report(stats, total, done)
        report_text = lib.format_report(report)
        tokens_line = f"spent_tokens={task_tokens}" if task_tokens is not None else "spent_tokens=unknown"
        report_lines = "\\n".join(f"`{line}`" for line in report_text.splitlines() if line.strip())
        tokens_line = f"`{tokens_line}`"
        if task_text:
            message = f"**Задача завершена**\\n{task_id} — {task_text}\\n\\n{tokens_line}\\n{report_lines}"
        else:
            message = f"**Задача завершена**\\n{task_id} — завершено\\n\\n{tokens_line}\\n{report_lines}"
        lib.log_event(log_path, "INFO", "stop: message prepared", task_id=task_id, text=message)
        lib.send_telegram_message(message, log_path)
        lib.save_stats(script_repo, stats)
        if loop_count < 5:
            sys.stdout.write(json.dumps({"followup_message": "commit EVERYTHING+push with task ID and task description as commit message"}))
            sys.stdout.flush()
    else:
        lib.log_event(log_path, "INFO", "stop: task not found in backlog", task_id=task_id)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""
    before_script = before_script.replace("__ORC_ROOT__", repr(str(orc_root)))
    stop_script = stop_script.replace("__ORC_ROOT__", repr(str(orc_root)))
    before_path.write_text(before_script, encoding="utf-8")
    stop_path.write_text(stop_script, encoding="utf-8")
    hook_lib_path.write_text(hook_lib_script, encoding="utf-8")
    before_path.chmod(0o755)
    stop_path.chmod(0o755)
    hook_lib_path.chmod(0o755)

    cursor_dir = Path(workdir) / ".cursor"
    if cursor_dir.exists():
        cursor_hooks_dir = cursor_dir / "hooks"
        cursor_hooks_dir.mkdir(parents=True, exist_ok=True)
        cursor_before = cursor_hooks_dir / "orc_before_submit.py"
        cursor_stop = cursor_hooks_dir / "orc_stop.py"
        cursor_hook_lib = cursor_hooks_dir / "orc_hook_lib.py"
        cursor_before.write_text(before_script, encoding="utf-8")
        cursor_stop.write_text(stop_script, encoding="utf-8")
        cursor_hook_lib.write_text(hook_lib_script, encoding="utf-8")
        cursor_before.chmod(0o755)
        cursor_stop.chmod(0o755)
        cursor_hook_lib.chmod(0o755)
    return before_path, stop_path


def ensure_repo_hooks_config(workdir: str, before_path: Path, stop_path: Path, log_path: Path) -> Path:
    def _ensure_hooks_file(hooks_path: Path, before_cmd: str, stop_cmd: str, label: str) -> None:
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        if hooks_path.exists():
            try:
                data = json.loads(hooks_path.read_text(encoding="utf-8"))
            except Exception as exc:
                log_event(log_path, "ERROR", f"{label}: bad JSON", error=str(exc))
                data = {}
        else:
            data = {}
        data.setdefault("version", 1)
        hooks = data.setdefault("hooks", {})
        before_list = hooks.setdefault("beforeSubmitPrompt", [])
        stop_list = hooks.setdefault("stop", [])

        if not any(item.get("command") == before_cmd for item in before_list if isinstance(item, dict)):
            before_list.append({"command": before_cmd})
            log_event(log_path, "INFO", f"{label}: added beforeSubmitPrompt", command=before_cmd)
        if not any(item.get("command") == stop_cmd for item in stop_list if isinstance(item, dict)):
            stop_list.append({"command": stop_cmd})
            log_event(log_path, "INFO", f"{label}: added stop", command=stop_cmd)

        hooks_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    hooks_path = Path(workdir) / ".orc" / "hooks.json"
    _ensure_hooks_file(hooks_path, f"python3 {before_path}", f"python3 {stop_path}", "hooks.json")

    cursor_dir = Path(workdir) / ".cursor"
    cursor_hooks_path = cursor_dir / "hooks.json"
    if cursor_dir.exists() or cursor_hooks_path.exists():
        cursor_before = cursor_dir / "hooks" / "orc_before_submit.py"
        cursor_stop = cursor_dir / "hooks" / "orc_stop.py"
        _ensure_hooks_file(
            cursor_hooks_path,
            f"python3 {cursor_before}",
            f"python3 {cursor_stop}",
            ".cursor/hooks.json",
        )
    return hooks_path


def write_task_file(workdir: str, task: Task, backlog_path: Path, log_path: Path, restart_count: int = 0) -> Path:
    task_path = Path(workdir) / ".orc" / "orc-task.json"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "task_id": task.task_id,
        "task_text": task.text,
        "backlog_path": str(backlog_path),
        "workspace_root": str(Path(workdir)),
        "conversation_id": "",
        "created_at": now_iso(),
        "restart_count": restart_count,
    }
    task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log_event(log_path, "INFO", "task file written", path=str(task_path), task_id=task.task_id)
    cursor_task_path = Path(workdir) / ".cursor" / "orc-task.json"
    if cursor_task_path.parent.exists():
        try:
            cursor_task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            log_event(log_path, "INFO", "task file mirrored", path=str(cursor_task_path), task_id=task.task_id)
        except Exception as exc:
            log_event(log_path, "ERROR", "failed to mirror task file", error=str(exc), path=str(cursor_task_path))
    return task_path


def update_task_restart_count(task_path: Path, log_path: Path, restart_count: int) -> None:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task file for restart update", error=str(exc))
        return
    payload["restart_count"] = restart_count
    try:
        task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to update task restart count", error=str(exc))
        return
    cursor_task_path = task_path.parents[1] / ".cursor" / task_path.name
    if cursor_task_path.exists():
        try:
            cursor_task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            log_event(log_path, "ERROR", "failed to update mirrored task file", error=str(exc), path=str(cursor_task_path))
