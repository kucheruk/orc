#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import orc_hook_lib as lib


def main() -> int:
    script_repo = Path(__file__).resolve().parents[2]
    orc_dir = script_repo / ".orc"
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

    task_file = script_repo / ".cursor" / "orc-task.json"
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

    if lib.mark_task_done(Path(backlog_path), task_id):
        lib.log_event(log_path, "INFO", "stop: marked task", task_id=task_id)
        try:
            task_file.unlink()
        except Exception as exc:
            lib.log_event(log_path, "ERROR", "stop: failed to delete task file", error=str(exc))
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
        report_lines = "\n".join(f"`{line}`" for line in report_text.splitlines() if line.strip())
        tokens_line = f"`{tokens_line}`"
        if task_text:
            message = f"**Задача завершена**\n{task_id} — {task_text}\n\n{tokens_line}\n{report_lines}"
        else:
            message = f"**Задача завершена**\n{task_id} — завершено\n\n{tokens_line}\n{report_lines}"
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
