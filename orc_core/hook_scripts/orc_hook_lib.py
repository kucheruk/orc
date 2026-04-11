#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

ORC_ROOT = Path(__ORC_ROOT__)
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
DEFAULT_LOG_LEVEL = "WARN"
if str(ORC_ROOT) not in sys.path:
    sys.path.insert(0, str(ORC_ROOT))
from orc_core.infra.atomic_io import write_json_atomic
from orc_core.infra.state_paths import artifacts_dir as external_artifacts_dir
from orc_core.infra.state_paths import metrics_path as external_metrics_path
from orc_core.infra.state_paths import stats_path as external_stats_path
from orc_core.tasks.task_source import MarkdownTaskSource

GIT_COMMAND_TIMEOUT_SECONDS = 20.0
ETA_WINDOW_SIZE = 3


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
    write_json_atomic(path, payload, ensure_ascii=False, indent=2)


def resolve_runtime_task_file(task_file: Path) -> Path:
    env_runtime_file = str(os.environ.get("ORC_TASK_RUNTIME_FILE") or "").strip()
    if env_runtime_file:
        return Path(env_runtime_file)
    return task_file.with_name("orc-task-runtime.json")


def read_task_active_seconds(runtime_task_file: Path, expected_task_id: str) -> float:
    payload = read_json(runtime_task_file, {})
    if not isinstance(payload, dict):
        return 0.0
    runtime_task_id = str(payload.get("task_id") or "").strip()
    if expected_task_id and runtime_task_id and runtime_task_id != expected_task_id:
        return 0.0
    try:
        return max(float(payload.get("active_seconds") or 0.0), 0.0)
    except (TypeError, ValueError):
        return 0.0


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
    import fcntl

    lock_file = Path(str(path) + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            return MarkdownTaskSource(path).mark_task_done(task_id)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def parse_backlog_counts(path: Path) -> Tuple[int, int]:
    tasks = MarkdownTaskSource(path).list_tasks()
    total = len(tasks)
    done = sum(1 for task in tasks if task.done)
    return total, done


def load_stats(repo_root: Path) -> Dict[str, object]:
    env_stats_path = str(os.environ.get("ORC_STATS_FILE") or "").strip()
    stats_path = Path(env_stats_path) if env_stats_path else external_stats_path(str(repo_root))
    data = read_json(stats_path, {})
    data.setdefault("created_at", now_iso())
    data.setdefault("started_at", data.get("started_at") or "")
    data.setdefault("tokens_total", int(data.get("tokens_total") or 0))
    data.setdefault("tokens_by_task", data.get("tokens_by_task") or {})
    data.setdefault("durations_by_task", data.get("durations_by_task") or {})
    data.setdefault("recent_durations", data.get("recent_durations") or [])
    data.setdefault("active_seconds_total", float(data.get("active_seconds_total") or 0.0))
    return data


def save_stats(repo_root: Path, stats: Dict[str, object]) -> None:
    env_stats_path = str(os.environ.get("ORC_STATS_FILE") or "").strip()
    stats_path = Path(env_stats_path) if env_stats_path else external_stats_path(str(repo_root))
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
    env_metrics_path = str(os.environ.get("ORC_METRICS_FILE") or "").strip()
    metrics_path = Path(env_metrics_path) if env_metrics_path else external_metrics_path(str(repo_root))
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


def record_task_duration(stats: Dict[str, object], task_id: str, duration_seconds: float) -> Dict[str, object]:
    task_key = str(task_id or "").strip()
    if not task_key:
        return stats
    durations_by_task = stats.setdefault("durations_by_task", {})
    if task_key in durations_by_task:
        return stats
    duration_int = max(int(duration_seconds), 0)
    durations_by_task[task_key] = duration_int
    recent = stats.setdefault("recent_durations", [])
    if not isinstance(recent, list):
        recent = []
        stats["recent_durations"] = recent
    recent.append(duration_int)
    stats["recent_durations"] = recent[-ETA_WINDOW_SIZE:]
    stats["active_seconds_total"] = float(stats.get("active_seconds_total") or 0.0) + float(duration_int)
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
    active_seconds_total = max(float(stats.get("active_seconds_total") or 0.0), 0.0)
    minutes = max(active_seconds_total / 60.0, 0.001)
    tokens_total = int(stats.get("tokens_total") or 0)
    tokens_per_min = tokens_total / minutes
    recent_raw = stats.get("recent_durations") or []
    recent = [max(int(value), 0) for value in recent_raw if isinstance(value, (int, float)) and value > 0]
    window = recent[-ETA_WINDOW_SIZE:]
    average_task_seconds = (sum(window) / len(window)) if window else 0.0
    tasks_per_hour = (3600.0 / average_task_seconds) if average_task_seconds > 0 else 0.0
    remaining = max(total_tasks - done_tasks, 0)
    eta = "unknown"
    if average_task_seconds > 0:
        eta = format_duration(average_task_seconds * remaining)
    return {
        "running_time": format_duration(active_seconds_total),
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


def normalize_path(raw: object, cwd: object = "") -> Path:
    text = str(raw or "").strip()
    base = Path(str(cwd or "").strip() or os.getcwd())
    if not text:
        return base.resolve()
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        return candidate.resolve()
    except Exception:
        return candidate


def is_path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except Exception:
        return False


def artifacts_dir(base_workspace: object) -> Path:
    return external_artifacts_dir(str(base_workspace or ""))


def is_artifact_path(path: object, base_workspace: object, cwd: object = "") -> bool:
    candidate = normalize_path(path, cwd)
    return is_path_within(candidate, artifacts_dir(base_workspace))


def extract_applypatch_paths(patch_text: object) -> list[str]:
    text = str(patch_text or "")
    if not text:
        return []
    pattern = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$", re.MULTILINE)
    return [match.strip() for match in pattern.findall(text) if str(match).strip()]
