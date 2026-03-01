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
        lib.log_event(log_path, "ERROR", "beforeSubmitPrompt: bad input", error=str(exc))
        data = {}

    roots = data.get("workspace_roots") or []
    if roots and str(script_repo) not in roots:
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: workspace mismatch", roots=roots)
        return 0

    task_file = script_repo / ".cursor" / "orc-task.json"
    lib.log_event(log_path, "INFO", "beforeSubmitPrompt", conversation_id=data.get("conversation_id"))
    if not task_file.exists():
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: no task file")
        return 0

    task = lib.read_json(task_file, {})
    if not isinstance(task, dict):
        lib.log_event(log_path, "ERROR", "beforeSubmitPrompt: invalid task payload type", payload_type=type(task).__name__)
        task = {}
    conv_id = str(data.get("conversation_id") or "").strip()
    existing_conv_id = str(task.get("conversation_id") or "").strip()
    task_changed = False
    if conv_id and existing_conv_id != conv_id:
        task["conversation_id"] = conv_id
        task_changed = True
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: stored conversation_id", conversation_id=conv_id)
    elif not conv_id:
        lib.log_event(log_path, "WARN", "beforeSubmitPrompt: payload conversation_id missing")
    else:
        lib.log_event(log_path, "INFO", "beforeSubmitPrompt: conversation_id unchanged")
    if task_changed:
        lib.write_json(task_file, task)

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
        message = f"**Старт задачи**\n{task_id} — {task_text}\n\n{report_text}"
        lib.log_event(log_path, "INFO", "start: message prepared", task_id=task_id, text=message)
        lib.send_telegram_message(message, log_path)
        task["start_notified"] = True
        lib.write_json(task_file, task)
        lib.save_stats(script_repo, stats)
        lib.log_event(log_path, "INFO", "start: notified", task_id=task_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
