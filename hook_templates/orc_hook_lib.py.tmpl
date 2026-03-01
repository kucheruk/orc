#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

ORC_ROOT = Path(__ORC_ROOT__)
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"
if str(ORC_ROOT) not in sys.path:
    sys.path.insert(0, str(ORC_ROOT))
from orc_core.task_source import MarkdownTaskSource

GIT_COMMAND_TIMEOUT_SECONDS = 20.0


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_event(path: Path, level: str, message: str, **fields):
    min_level = LOG_LEVELS.get(os.environ.get("ORC_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper().strip(), LOG_LEVELS[DEFAULT_LOG_LEVEL])
    if LOG_LEVELS.get(level.upper(), 100) < min_level:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": now_iso(), "level": level, "message": message, **fields}
    with path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


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


def is_task_marked(path: Path, task_id: str) -> bool:
    return MarkdownTaskSource(path).is_task_done(task_id)


def mark_task_done(path: Path, task_id: str) -> bool:
    return MarkdownTaskSource(path).mark_task_done(task_id)


def parse_backlog_counts(path: Path) -> Tuple[int, int]:
    tasks = MarkdownTaskSource(path).list_tasks()
    total = len(tasks)
    done = sum(1 for task in tasks if task.done)
    return total, done


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
    return "\n".join(
        [
            f"running_time={report['running_time']}",
            f"tokens_total={report['tokens_total']}",
            f"tokens_per_min={report['tokens_per_min']:.1f}",
            f"tasks_per_hour={report['tasks_per_hour']:.2f}",
            f"eta={report['eta']}",
            f"tasks_remaining={report['tasks_remaining']}",
        ]
    )
