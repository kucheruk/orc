#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .backlog import find_first_open_task, is_task_done, parse_backlog, render_progress
from .hooks import (
    ensure_repo_hooks,
    ensure_repo_hooks_config,
    update_task_restart_count,
    write_task_file,
)
from .logging import ORC_LOG_NAME, ORC_ROOT, debug_log, log_event
from .notify import send_telegram_message
from .process import acquire_lock, kill_process_tree, release_lock
from .runner import launch_agent_with_ht
from .text_parse import clean_summary_lines

TASK_FILE_NAME = "orc-task.json"
LOCK_FILE_NAME = "orc.lock"

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_PATH = BASE_DIR / "prompts" / "default.txt"
CONTINUE_PROMPT_PATH = BASE_DIR / "prompts" / "continue.txt"


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _write_prompt_file(run_root: Path, prompt: str, tag: str) -> Path:
    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{tag}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _update_task_conversation_id(task_path: Path, log_path: Path, conversation_id: str) -> None:
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


def _parse_agent_ls_output(output: str) -> Optional[str]:
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


def _get_resume_id_from_agent_ls(workdir: str, log_path: Path) -> Optional[str]:
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
    resume_id = _parse_agent_ls_output(result.stdout)
    if resume_id:
        log_event(log_path, "INFO", "agent ls resume id", conversation_id=resume_id)
    else:
        log_event(log_path, "WARN", "agent ls returned no resume id")
    return resume_id


def wait_for_completion(
    task_path: Path,
    monitor,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    log_path: Path,
    nudge_after: int,
    nudge_cooldown: float,
    nudge_text: str,
    task_id: str,
    task_text: str,
) -> str:
    start_time = time.time()
    last_stats_key: Optional[Tuple[int, int, int, int]] = None
    same_count = 0
    last_tokens_value: Optional[int] = None
    last_tokens_time = time.time()
    last_stuck_notice_time = 0.0
    #region agent log
    debug_log(
        "H3",
        "orc_core/supervisor.py:wait_for_completion:start",
        "wait loop start",
        {
            "task_path": str(task_path),
            "exists": task_path.exists(),
            "stall_timeout": stall_timeout,
            "task_ttl": task_ttl,
            "poll": poll,
        },
    )
    #endregion
    while task_path.exists():
        monitor.maybe_report()
        stats_key = (
            monitor.metrics.total_lines,
            monitor.metrics.command_count,
            monitor.metrics.total_output_chars,
            int(monitor.metrics.tokens_total or 0),
        )
        tokens_value = monitor.metrics.tokens_total
        if tokens_value is not None:
            if last_tokens_value is None or tokens_value != last_tokens_value:
                last_tokens_value = tokens_value
                last_tokens_time = time.time()
            else:
                since_tokens = time.time() - last_tokens_time
                if since_tokens >= 300 and (time.time() - last_stuck_notice_time) >= 300:
                    last_stuck_notice_time = time.time()
                    stuck_msg = f"{task_id} — agent stuck (tokens unchanged 5m)"
                    if task_text:
                        stuck_msg = f"{task_id} — {task_text}\nagent stuck (tokens unchanged 5m)"
                    send_telegram_message(stuck_msg, log_path)
        if stats_key == last_stats_key:
            same_count += 1
        else:
            same_count = 0
            last_stats_key = stats_key
        # Auto-continue removed (was unreliable and noisy).
        if monitor.proc.poll() is not None:
            log_event(log_path, "ERROR", "ht process exited while task still active", returncode=monitor.proc.returncode)
            #region agent log
            debug_log(
                "H4",
                "orc_core/supervisor.py:wait_for_completion:exit",
                "ht process exited early",
                {
                    "returncode": monitor.proc.returncode,
                    "task_exists": task_path.exists(),
                    "stderr_count": monitor.stderr_count,
                    "last_stderr_line": monitor.last_stderr_line,
                },
            )
            #endregion
            return "process_exited"
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", stall_seconds=stall_timeout)
            #region agent log
            debug_log(
                "H5",
                "orc_core/supervisor.py:wait_for_completion:stall",
                "stall detected",
                {
                    "stall_seconds": stall_timeout,
                    "since_last_output": time.time() - monitor.last_output_time,
                    "lines": monitor.metrics.total_lines,
                    "task_exists": task_path.exists(),
                },
            )
            #endregion
            return "stalled"
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "task ttl exceeded", task_ttl=task_ttl)
            #region agent log
            debug_log(
                "H6",
                "orc_core/supervisor.py:wait_for_completion:ttl",
                "task ttl exceeded",
                {"task_ttl": task_ttl, "elapsed": time.time() - start_time},
            )
            #endregion
            return "ttl_exceeded"
        time.sleep(max(poll, 0.2))
    log_event(log_path, "INFO", "task file removed; completion observed")
    #region agent log
    debug_log(
        "H3",
        "orc_core/supervisor.py:wait_for_completion:done",
        "task file removed",
        {"task_path": str(task_path)},
    )
    #endregion
    return "completed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="BACKLOG.md")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--model", default="gpt-5.2-codex")
    ap.add_argument("--prompt-template", default="", help="Path to a custom prompt template file")
    ap.add_argument("--continue-template", default="", help="Path to a custom continue prompt file")
    ap.add_argument("--poll", type=float, default=1.0, help="Poll interval for task completion")
    ap.add_argument("--stall-timeout", type=float, default=600.0, help="Seconds without output before stall")
    ap.add_argument("--task-ttl", type=float, default=6 * 3600, help="Max seconds per task before abort")
    ap.add_argument("--max-restarts", type=int, default=2, help="Max restarts for a task")
    ap.add_argument("--report-interval", type=float, default=15.0, help="Seconds between stats reports")
    ap.add_argument("--summary-lines", type=int, default=25, help="Lines to send to Telegram after completion")
    ap.add_argument("--ht-listen", default="", help="Optional ht listen address (e.g. 127.0.0.1:0)")
    ap.add_argument("--nudge-after", type=int, default=10, help="Send continue after N identical stats")
    ap.add_argument("--nudge-cooldown", type=float, default=300.0, help="Seconds between auto-nudges")
    ap.add_argument("--nudge-text", default="continue", help="Text to send before Enter")
    ap.add_argument("--telegram-test", nargs="?", const="orc telegram test", default=None, help="Send a test Telegram message and exit")
    ap.add_argument("--reinit-hooks", action="store_true", help="Recreate hooks on startup")
    args = ap.parse_args()

    workdir = str(Path(args.workspace).resolve())
    backlog_path = Path(workdir) / args.backlog
    orc_log_path = ORC_ROOT / ".orc" / ORC_LOG_NAME
    lock_path = Path(workdir) / ".orc" / LOCK_FILE_NAME

    if args.telegram_test is not None:
        send_telegram_message(args.telegram_test, orc_log_path)
        return 0

    if args.reinit_hooks:
        before_path, stop_path = ensure_repo_hooks(workdir)
        hooks_path = ensure_repo_hooks_config(workdir, before_path, stop_path, orc_log_path)
        log_event(orc_log_path, "WARN", "hooks reinitialized", hooks_config=str(hooks_path))

    if not backlog_path.exists():
        print(f"Backlog not found: {backlog_path}", file=sys.stderr)
        return 2

    acquire_lock(lock_path, orc_log_path)
    active_monitor = None
    try:
        try:
            template = load_prompt(Path(args.prompt_template)) if args.prompt_template else load_prompt(DEFAULT_PROMPT_PATH)
            continue_prompt = load_prompt(Path(args.continue_template)) if args.continue_template else load_prompt(CONTINUE_PROMPT_PATH)
        except FileNotFoundError as exc:
            log_event(orc_log_path, "ERROR", "prompt file missing", error=str(exc))
            return 2

        task_path = Path(workdir) / ".orc" / TASK_FILE_NAME
        run_root = Path(workdir) / ".orc" / "backlog-run"
        while True:
            tasks = parse_backlog(backlog_path)
            total = len(tasks)
            done = sum(1 for t in tasks if t.done)
            open_task = find_first_open_task(backlog_path)

            print("\n" + render_progress(done, total))
            if not open_task:
                log_event(orc_log_path, "INFO", "backlog complete")
                print("✅ BACKLOG.md: невыполненных пунктов не осталось. Выход.")
                return 0

            task_id = open_task.task_id
            task_text = open_task.text

            resume_existing = task_path.exists()
            resume_id: Optional[str] = None
            resume_latest = False
            #region agent log
            debug_log(
                "H2",
                "orc_core/supervisor.py:main:task_state",
                "task file state",
                {"task_path": str(task_path), "exists": resume_existing},
            )
            #endregion
            if resume_existing:
                try:
                    active = json.loads(task_path.read_text(encoding="utf-8"))
                    active_task_id = active.get("task_id")
                    active_task_text = active.get("task_text")
                    resume_id = (active.get("conversation_id") or "").strip() or None
                    #region agent log
                    debug_log(
                        "H2",
                        "orc_core/supervisor.py:main:resume_existing",
                        "resume task loaded",
                        {"active_task_id": active_task_id, "task_text_len": len(active_task_text) if active_task_text else 0},
                    )
                    #endregion
                except Exception as exc:
                    log_event(orc_log_path, "ERROR", "failed to read task file", error=str(exc))
                    print(f"⚠️ Не удалось прочитать {task_path}. Удали файл и запусти заново.")
                    time.sleep(max(args.poll, 0.2))
                    continue
                if active_task_id and is_task_done(backlog_path, active_task_id):
                    log_event(orc_log_path, "INFO", "task already marked done; removing task file", task_id=active_task_id)
                    print(f"✅ {active_task_id} уже отмечена [x]. Удаляю {task_path} и продолжаю.")
                    try:
                        task_path.unlink()
                    except Exception as exc:
                        log_event(orc_log_path, "ERROR", "failed to delete task file", error=str(exc))
                    continue
                # Файл актуален — используем его данные для resume
                task_id = active_task_id or task_id
                task_text = active_task_text or task_text
                log_event(orc_log_path, "INFO", "resume existing task", task_id=task_id)
                print(f"↩️ Обнаружена активная задача, запускаю resume для {task_id}.")
                if not resume_id:
                    resume_id = _get_resume_id_from_agent_ls(workdir, orc_log_path)
                    if resume_id:
                        _update_task_conversation_id(task_path, orc_log_path, resume_id)
                resume_latest = resume_id is None
                log_event(
                    orc_log_path,
                    "INFO",
                    "resume selection",
                    conversation_id=resume_id or "",
                    resume_latest=resume_latest,
                )

            short = (task_text[:120] + "…") if len(task_text) > 120 else task_text
            print(f"▶️ Текущая задача: {task_id} — {short}")

            before_path, stop_path = ensure_repo_hooks(workdir)
            hooks_path = ensure_repo_hooks_config(workdir, before_path, stop_path, orc_log_path)
            log_event(orc_log_path, "INFO", "hooks ready", hooks_config=str(hooks_path))

            if not resume_existing:
                write_task_file(workdir, open_task, backlog_path, orc_log_path, restart_count=0)

            prompt_vars = SafeDict(task_text=task_text, task_id=task_id, backlog=args.backlog, workspace=workdir)
            prompt = template.format_map(prompt_vars)

            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_text)[:60]
            tag = f"{ts}__{safe_name}"
            prompt_path = _write_prompt_file(run_root, prompt, tag)

            restart_count = 0
            while True:
                update_task_restart_count(task_path, orc_log_path, restart_count)
                log_event(orc_log_path, "INFO", "launching agent", task_id=task_id, restart_count=restart_count)
                try:
                    active_monitor = launch_agent_with_ht(
                        workdir,
                        prompt_path,
                        args.model,
                        orc_log_path,
                        report_interval=args.report_interval,
                        summary_lines=args.summary_lines,
                        listen_addr=args.ht_listen,
                        task_id=task_id,
                        resume_id=resume_id if resume_existing else None,
                        resume_latest=resume_existing and resume_id is None,
                        resume_prompt=args.nudge_text if resume_existing else None,
                    )
                except FileNotFoundError:
                    print("❌ ht не найден. Установите ht и попробуйте снова.")
                    return 2
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=active_monitor,
                    poll=args.poll,
                    stall_timeout=args.stall_timeout,
                    task_ttl=args.task_ttl,
                    log_path=orc_log_path,
                    nudge_after=args.nudge_after,
                    nudge_cooldown=args.nudge_cooldown,
                    nudge_text=args.nudge_text,
                    task_id=task_id,
                    task_text=task_text,
                )
                active_monitor.stop()
                kill_process_tree(active_monitor.init_pid or active_monitor.proc.pid, orc_log_path, label="agent")
                #region agent log
                debug_log(
                    "H8",
                    "orc_core/supervisor.py:main:completion_state",
                    "completion state",
                    {
                        "result": result,
                        "monitor_is_none": active_monitor is None,
                        "lines": active_monitor.metrics.total_lines,
                        "commands": active_monitor.metrics.command_count,
                        "tokens_total": active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-",
                    },
                )
                #endregion
                if result == "completed":
                    log_event(orc_log_path, "INFO", "task completed", task_id=task_id)
                    raw_summary_text = active_monitor.get_summary_text()
                    raw_lines = raw_summary_text.splitlines() if raw_summary_text else []
                    cleaned_lines = clean_summary_lines(raw_lines)
                    summary_text = "\n".join(cleaned_lines[-args.summary_lines :])
                    tokens = active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-"
                    files_edited = active_monitor.metrics.files_edited if active_monitor.metrics.files_edited is not None else "-"
                    print(
                        f"[orc] completed stats tokens={tokens} lines={active_monitor.metrics.total_lines} "
                        f"commands={active_monitor.metrics.command_count} files_edited={files_edited}",
                        flush=True,
                    )
                    #region agent log
                    debug_log(
                        "H8",
                        "orc_core/supervisor.py:main:summary",
                        "summary prepared",
                        {
                            "summary_len": len(summary_text),
                            "summary_lines": summary_text.count("\n") + 1 if summary_text else 0,
                        },
                    )
                    #endregion
                    # Telegram notifications are handled by hooks.
                    if not summary_text.strip():
                        log_event(orc_log_path, "WARN", "telegram summary empty", task_id=task_id)
                    active_monitor = None
                    break
                active_monitor = None
                restart_count += 1
                if restart_count > args.max_restarts:
                    log_event(orc_log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                    #region agent log
                    debug_log(
                        "H6",
                        "orc_core/supervisor.py:main:max_restarts",
                        "max restarts exceeded",
                        {"task_id": task_id, "restart_count": restart_count, "max_restarts": args.max_restarts},
                    )
                    #endregion
                    print("❌ Агент не завершил задачу. Проверь логи.")
                    return 1
                log_event(orc_log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
                prompt = continue_prompt.format_map(prompt_vars)
                prompt_path = _write_prompt_file(run_root, prompt, f"{tag}__r{restart_count}")
            print("[orc] pause 5s before next task (Ctrl+C to stop)", flush=True)
            time.sleep(5)
    except KeyboardInterrupt:
        log_event(orc_log_path, "WARN", "keyboard interrupt")
        print("⏹️ Прервано. Состояние сохранено.")
        return 130
    finally:
        if active_monitor is not None:
            active_monitor.stop()
            kill_process_tree(active_monitor.init_pid or active_monitor.proc.pid, orc_log_path, label="agent-finalize")
        release_lock(lock_path, orc_log_path)


if __name__ == "__main__":
    raise SystemExit(main())
