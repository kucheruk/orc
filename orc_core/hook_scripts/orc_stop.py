#!/usr/bin/env python3
# ORC_HOOK_VERSION=2
import json
import os
import sys
from pathlib import Path

import orc_hook_lib as lib
from orc_core.state_paths import active_task_path, hook_log_path


def _norm_path(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        return str(Path(text).resolve())
    except Exception:
        return text


def main() -> int:
    script_repo = Path(__file__).resolve().parents[2]
    base_workspace = Path(str(os.environ.get("ORC_BASE_WORKSPACE") or "").strip() or str(script_repo))
    log_path = hook_log_path(str(base_workspace))
    try:
        raw = sys.stdin.read() or "{}"
        data = json.loads(raw)
    except Exception as exc:
        lib.log_event(log_path, "ERROR", "stop: bad input", error=str(exc))
        data = {}

    roots = data.get("workspace_roots") or []
    allowed_roots = {_norm_path(str(script_repo)), _norm_path(str(base_workspace))}
    normalized_roots = {_norm_path(str(root)) for root in roots}
    if normalized_roots and not normalized_roots.intersection(allowed_roots):
        lib.log_event(log_path, "INFO", "stop: workspace mismatch", roots=roots)
        return 0

    env_task_file = str(os.environ.get("ORC_TASK_FILE") or "").strip()
    task_file = Path(env_task_file) if env_task_file else active_task_path(str(base_workspace))
    runtime_task_file = lib.resolve_runtime_task_file(task_file)
    lib.log_event(log_path, "INFO", "stop: task file resolved", task_file=str(task_file))
    lib.log_event(log_path, "INFO", "stop: runtime task file resolved", runtime_task_file=str(runtime_task_file))
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

    conv_id = str(data.get("conversation_id") or "").strip()
    task_conversation_id = str(task.get("conversation_id") or "").strip()
    if conv_id and not task_conversation_id:
        task["conversation_id"] = conv_id
        task_conversation_id = conv_id
        lib.write_json(task_file, task)
        lib.log_event(log_path, "INFO", "stop: backfilled conversation_id", conversation_id=conv_id)
    if task_conversation_id and conv_id and task_conversation_id != conv_id:
        lib.log_event(
            log_path,
            "WARN",
            "stop: conversation_id mismatch (continuing)",
            task_conversation_id=task_conversation_id,
            got_conversation_id=conv_id,
        )

    backlog_path = task.get("backlog_path")
    task_id = task.get("task_id")
    if not backlog_path or not task_id:
        lib.log_event(log_path, "ERROR", "stop: missing backlog_path/task_id")
        return 0
    status = data.get("status")
    stage_id = str(task.get("sdlc_stage_id") or "").strip()
    stage_is_final = bool(task.get("sdlc_stage_is_final")) if stage_id else True
    if status == "completed" and not stage_is_final:
        lib.log_event(
            log_path,
            "INFO",
            "stop: completed intermediate sdlc stage; skip backlog completion",
            task_id=task_id,
            stage_id=stage_id,
        )
        return 0
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
        created_at = str(task.get("created_at") or "").strip()
        if lib.git_has_recent_commit(script_repo, created_at, log_path):
            lib.log_event(log_path, "INFO", "stop: recent commit detected; proceeding", task_id=task_id)
        else:
            lib.log_event(log_path, "WARN", "stop: completed without new commit or local changes", task_id=task_id)
            return 0

    # Task completion: clean up state files, track stats.
    # BACKLOG.md marking is done by the agent via prompt instructions (not by hook).
    lib.log_event(log_path, "INFO", "stop: task completed", task_id=task_id)
    try:
        task_file.unlink()
    except Exception as exc:
        lib.log_event(log_path, "ERROR", "stop: failed to delete task file", error=str(exc))
    try:
        runtime_task_file.unlink()
    except FileNotFoundError:
        pass
    except Exception as exc:
        lib.log_event(log_path, "ERROR", "stop: failed to delete runtime task file", error=str(exc))
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
    stats = lib.load_stats(base_workspace)
    task_tokens = lib.read_task_tokens(script_repo)
    stats = lib.update_tokens(stats, task_id, task_tokens)
    task_active_seconds = lib.read_task_active_seconds(runtime_task_file, str(task_id))
    stats = lib.record_task_duration(stats, task_id, task_active_seconds)
    report = lib.build_report(stats, total, done)
    report_text = lib.format_report(report)
    tokens_line = f"spent_tokens={task_tokens}" if task_tokens is not None else "spent_tokens=unknown"
    lib.log_event(
        log_path,
        "INFO",
        "stop: completion tracked",
        task_id=task_id,
        task_text=task_text,
        tokens=tokens_line,
        report=report_text,
    )
    lib.save_stats(base_workspace, stats)
    if loop_count < 5:
        sys.stdout.write(json.dumps({"followup_message": "commit EVERYTHING+push with task ID and task description as commit message"}))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
