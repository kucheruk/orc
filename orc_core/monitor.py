#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, List, Optional

from .logging import DEBUG_RAW_LOG_PATH, debug_log, log_event
from .process import build_process_tree
from .text_parse import (
    BOX_LINE_RE,
    FILES_EDITED_RE,
    extract_files_edited_from_text,
    extract_live_lines,
    extract_tokens_from_line,
    extract_tokens_from_text,
    is_status_only_output,
    looks_like_command,
    split_compacted_lines,
    strip_ansi,
)


@dataclass
class MetricsStore:
    tokens_total: Optional[int] = None
    tokens_line_hits: int = 0
    files_edited: Optional[int] = None
    command_count: int = 0
    total_lines: int = 0
    total_output_chars: int = 0
    git_added: Optional[int] = None
    git_deleted: Optional[int] = None
    proc_count: Optional[int] = None
    proc_cpu: Optional[float] = None
    proc_rss_mb: Optional[float] = None
    last_note: str = ""
    last_note_time: float = 0.0


class MetricsRenderer:
    def format_stats(self, metrics: MetricsStore, status_only: bool) -> Dict[str, object]:
        tokens = metrics.tokens_total if metrics.tokens_total is not None else "-"
        files_edited = metrics.files_edited if metrics.files_edited is not None else "-"
        git_stats = "-"
        if metrics.git_added is not None and metrics.git_deleted is not None:
            git_stats = f"+{metrics.git_added}/-{metrics.git_deleted}"
        proc_stats = "-"
        if metrics.proc_count is not None and metrics.proc_cpu is not None and metrics.proc_rss_mb is not None:
            proc_stats = f"p={metrics.proc_count} cpu={metrics.proc_cpu}% rss={metrics.proc_rss_mb}MB"
        return {
            "tokens": tokens,
            "files_edited": files_edited,
            "git_stats": git_stats,
            "proc_stats": proc_stats,
            "status_only": status_only,
            "note": metrics.last_note,
        }

    def format_live_metrics(self, task_id: str, metrics: MetricsStore) -> str:
        git_stats = "-"
        if metrics.git_added is not None and metrics.git_deleted is not None:
            git_stats = f"+{metrics.git_added}/-{metrics.git_deleted}"
        proc_stats = ""
        if metrics.proc_count is not None and metrics.proc_cpu is not None and metrics.proc_rss_mb is not None:
            proc_stats = f" p={metrics.proc_count} cpu={metrics.proc_cpu}% rss={metrics.proc_rss_mb}MB"
        note = ""
        if metrics.last_note and (time.time() - metrics.last_note_time) < 120:
            note = f" note={metrics.last_note}"
        return (
            f"id={task_id} tokens={metrics.tokens_total or '-'} "
            f"commands={metrics.command_count} files_edited={metrics.files_edited or '-'} git={git_stats}{proc_stats}{note}"
        )
 
    def format_live_block(self, task_id: str, metrics: MetricsStore, output_line: str, status_line: str) -> str:
        metrics_text = self.format_live_metrics(task_id, metrics)
        return f"{output_line}\n{status_line}  [{metrics_text}]"


class HtMonitor:
    def __init__(
        self,
        proc,
        log_path: Path,
        report_interval: float,
        summary_lines: int,
        task_id: str,
        workdir: str,
        renderer: Optional[MetricsRenderer] = None,
    ) -> None:
        self.proc = proc
        self.log_path = log_path
        self.task_id = task_id
        self.workdir = workdir
        self.renderer = renderer or MetricsRenderer()
        self.metrics = MetricsStore()
        self.last_output_time = time.time()
        self.init_pid: Optional[int] = None
        self.monitor_id = f"mon-{id(self)}"
        self._last_git_stats_time = 0.0
        self._last_proc_stats_time = 0.0
        self._line_buffer = ""
        self._last_lines: Deque[str] = deque(maxlen=max(summary_lines, 1))
        self._raw_lines: Deque[str] = deque(maxlen=1000)
        self._raw_chunks: Deque[str] = deque(maxlen=500)
        self._last_report_time = 0.0
        self._last_raw_dump_time = 0.0
        self.report_interval = max(report_interval, 1.0)
        self._debug_first_output_logged = False
        self._debug_first_stderr_logged = False
        self._debug_first_line_logged = False
        self._debug_first_token_logged = False
        self.last_stderr_line = ""
        self.stderr_count = 0
        self._stdin_lock = threading.Lock()
        self.last_nudge_time = 0.0
        self.status_only_reports = 0
        self._last_snapshot_time = 0.0
        self._last_snapshot_lines: List[str] = []
        self._last_live_block = ""
        self._has_live_status = False
        self.ui_prompt_continue_lines = 0
        self.ui_has_review_hint = False
        self.ui_sessions_menu = False
        self.ui_followup_prompt = False
        self.ui_empty_prompt = False
        self._stop = threading.Event()
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()
        #region agent log
        debug_log(
            "H13",
            "orc_core/monitor.py:HtMonitor.__init__",
            "monitor created",
            {
                "monitor_id": self.monitor_id,
                "report_interval": self.report_interval,
                "summary_lines": summary_lines,
                "task_id": self.task_id,
                "workdir": self.workdir,
            },
        )
        #endregion

    def _record_text(self, seq: str) -> None:
        cleaned = strip_ansi(seq).replace("\r", "")
        self.metrics.total_output_chars += len(cleaned)
        if cleaned:
            self._raw_chunks.append(cleaned)
        tokens = extract_tokens_from_text(cleaned)
        if tokens is not None:
            prev_tokens = self.metrics.tokens_total or 0
            self.metrics.tokens_total = max(prev_tokens, tokens)
            #region agent log
            debug_log(
                "H13",
                "orc_core/monitor.py:HtMonitor._record_text:tokens_update",
                "tokens updated",
                {"monitor_id": self.monitor_id, "prev": prev_tokens, "new": self.metrics.tokens_total},
            )
            #endregion
            #region agent log
            debug_log(
                "H10",
                "orc_core/monitor.py:HtMonitor._record_text:tokens",
                "tokens parsed from chunk",
                {"tokens": tokens},
            )
            #endregion
        elif "tokens" in cleaned.lower():
            #region agent log
            debug_log(
                "H10",
                "orc_core/monitor.py:HtMonitor._record_text:tokens_miss",
                "tokens present but regex miss",
                {"sample": cleaned[:200]},
            )
            #endregion
            idx = cleaned.lower().find("tokens")
            if idx >= 0:
                snippet = cleaned[max(0, idx - 20) : idx + 20]
                #region agent log
                debug_log(
                    "H12",
                    "orc_core/monitor.py:HtMonitor._record_text:tokens_codepoints",
                    "tokens snippet codepoints",
                    {"snippet": snippet, "codepoints": [ord(c) for c in snippet]},
                )
                #endregion
        files_edited = extract_files_edited_from_text(cleaned)
        if files_edited is not None:
            self.metrics.files_edited = max(self.metrics.files_edited or 0, files_edited)
            #region agent log
            debug_log(
                "H11",
                "orc_core/monitor.py:HtMonitor._record_text:files_edited",
                "files_edited parsed from chunk",
                {"files_edited": files_edited},
            )
            #endregion
        elif "files edited" in cleaned.lower():
            #region agent log
            debug_log(
                "H11",
                "orc_core/monitor.py:HtMonitor._record_text:files_edited_miss",
                "files edited present but regex miss",
                {"sample": cleaned[:200]},
            )
            #endregion
            idx = cleaned.lower().find("files edited")
            if idx >= 0:
                snippet = cleaned[max(0, idx - 20) : idx + 20]
                #region agent log
                debug_log(
                    "H12",
                    "orc_core/monitor.py:HtMonitor._record_text:files_edited_codepoints",
                    "files edited snippet codepoints",
                    {"snippet": snippet, "codepoints": [ord(c) for c in snippet]},
                )
                #endregion
        parts = cleaned.split("\n")
        if len(parts) == 1:
            self._line_buffer += parts[0]
            buffered_tokens = extract_tokens_from_text(self._line_buffer)
            if buffered_tokens is not None:
                self.metrics.tokens_total = max(self.metrics.tokens_total or 0, buffered_tokens)
            buffered_files = extract_files_edited_from_text(self._line_buffer)
            if buffered_files is not None:
                self.metrics.files_edited = max(self.metrics.files_edited or 0, buffered_files)
            return
        first = self._line_buffer + parts[0]
        self._process_line(first)
        for middle in parts[1:-1]:
            self._process_line(middle)
        self._line_buffer = parts[-1]
        buffered_tokens = extract_tokens_from_text(self._line_buffer)
        if buffered_tokens is not None:
            self.metrics.tokens_total = max(self.metrics.tokens_total or 0, buffered_tokens)
        buffered_files = extract_files_edited_from_text(self._line_buffer)
        if buffered_files is not None:
            self.metrics.files_edited = max(self.metrics.files_edited or 0, buffered_files)

    def _process_line(self, line: str) -> None:
        if not line and not self._last_lines:
            return
        self.metrics.total_lines += 1
        if looks_like_command(line):
            self.metrics.command_count += 1
        tokens = extract_tokens_from_line(line)
        if tokens is not None:
            self.metrics.tokens_total = max(self.metrics.tokens_total or 0, tokens)
            self.metrics.tokens_line_hits += 1
            if not self._debug_first_token_logged:
                self._debug_first_token_logged = True
                #region agent log
                debug_log(
                    "H7",
                    "orc_core/monitor.py:HtMonitor._process_line:tokens",
                    "tokens detected",
                    {"tokens": tokens, "line_len": len(line)},
                )
                #endregion
        files_match = FILES_EDITED_RE.search(line)
        if files_match:
            try:
                self.metrics.files_edited = max(self.metrics.files_edited or 0, int(files_match.group(1)))
            except ValueError:
                pass
        if not self._debug_first_line_logged:
            self._debug_first_line_logged = True
            #region agent log
            debug_log(
                "H7",
                "orc_core/monitor.py:HtMonitor._process_line:first_line",
                "first line parsed",
                {"line_len": len(line)},
            )
            #endregion
        self._last_lines.append(line)
        self._raw_lines.append(line)
        log_event(self.log_path, "INFO", "agent_line", line=line[:500])

    def maybe_report(self) -> None:
        now = time.time()
        if now - self._last_report_time < self.report_interval:
            return
        self._last_report_time = now
        last_output_age = now - self.last_output_time
        proc_status = self.proc.poll()
        status_only = is_status_only_output(self._raw_lines)
        if status_only:
            self.status_only_reports += 1
        else:
            self.status_only_reports = 0
        if now - self._last_git_stats_time >= 10.0:
            self._last_git_stats_time = now
            self.update_git_stats()
        if now - self._last_proc_stats_time >= 10.0:
            self._last_proc_stats_time = now
            self.update_process_stats()
        rendered = self.renderer.format_stats(self.metrics, status_only)
        tokens = rendered["tokens"]
        files_edited = rendered["files_edited"]
        git_stats = rendered["git_stats"]
        proc_stats = rendered["proc_stats"]
        note = rendered.get("note") or ""
        self._write_metrics_snapshot()
        if now - self._last_snapshot_time >= self.report_interval:
            self._last_snapshot_time = now
            if self.send_command({"type": "takeSnapshot"}):
                #region agent log
                debug_log(
                    "H15",
                    "orc_core/monitor.py:HtMonitor.maybe_report:take_snapshot",
                    "snapshot requested",
                    {"monitor_id": self.monitor_id},
                )
                #endregion
        if now - self._last_raw_dump_time >= 3.0:
            self._last_raw_dump_time = now
            try:
                DEBUG_RAW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                if self._last_snapshot_lines:
                    tail = self._last_snapshot_lines[-1000:]
                else:
                    combined = "".join(self._raw_chunks)
                    lines = combined.splitlines()
                    if len(lines) <= 1:
                        lines = split_compacted_lines(combined)
                    tail = lines[-1000:]
                DEBUG_RAW_LOG_PATH.write_text("\n".join(tail) + "\n", encoding="utf-8")
                #region agent log
                debug_log(
                    "H14",
                    "orc_core/monitor.py:HtMonitor.maybe_report:raw_dump",
                    "debug-raw written",
                    {
                        "monitor_id": self.monitor_id,
                        "raw_lines": len(tail),
                        "combined_len": len("".join(self._raw_chunks)),
                        "first_len": len(tail[0]) if tail else 0,
                        "last_len": len(tail[-1]) if tail else 0,
                    },
                )
                #endregion
            except Exception as exc:
                log_event(self.log_path, "ERROR", "debug raw dump failed", error=str(exc))
        #region agent log
        debug_log(
            "H7",
            "orc_core/monitor.py:HtMonitor.maybe_report",
            "stats report",
            {
                "monitor_id": self.monitor_id,
                "tokens": tokens,
                "lines": self.metrics.total_lines,
                "commands": self.metrics.command_count,
                "files_edited": files_edited,
                "git_stats": git_stats,
                "proc_stats": proc_stats,
                "output_chars": self.metrics.total_output_chars,
                "buffer_len": len(self._line_buffer),
                "last_output_age": last_output_age,
                "proc_status": proc_status,
                "status_only": status_only,
                "status_only_reports": self.status_only_reports,
                "raw_lines": len(self._raw_lines),
            },
        )
        #endregion
        log_event(
            self.log_path,
            "INFO",
            "stats report",
            tokens=tokens,
            lines=self.metrics.total_lines,
            commands=self.metrics.command_count,
            files_edited=files_edited,
            status_only=status_only,
            git_stats=git_stats,
            proc_stats=proc_stats,
        )
        if not self._has_live_status:
            note_suffix = f" note={note}" if note else ""
            sys.stdout.write(
                "\r\x1b[2K"
                + f"[orc] stats tokens={tokens} lines={self.metrics.total_lines} commands={self.metrics.command_count} "
                + f"files_edited={files_edited} git={git_stats} {proc_stats}{note_suffix}"
            )
            sys.stdout.flush()

    def get_summary_text(self) -> str:
        if self._line_buffer:
            self._process_line(self._line_buffer)
            self._line_buffer = ""
        return "\n".join(self._last_lines)

    def _write_metrics_snapshot(self) -> None:
        try:
            payload = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "task_id": self.task_id,
                "tokens_total": self.metrics.tokens_total,
                "lines": self.metrics.total_lines,
                "commands": self.metrics.command_count,
                "files_edited": self.metrics.files_edited,
            }
            path = Path(self.workdir) / ".orc" / "orc-metrics.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            log_event(self.log_path, "ERROR", "metrics snapshot write failed", error=str(exc))

    def send_command(self, payload: Dict[str, object]) -> bool:
        if self.proc.stdin is None:
            log_event(self.log_path, "ERROR", "ht stdin unavailable")
            return False
        try:
            with self._stdin_lock:
                self.proc.stdin.write(json.dumps(payload) + "\n")
                self.proc.stdin.flush()
            return True
        except Exception as exc:
            log_event(self.log_path, "ERROR", "ht command failed", error=str(exc))
            return False

    def update_live_status(self, lines: List[str]) -> None:
        live = extract_live_lines(lines)
        if not live:
            return
        output_line, status_line = live
        metrics_text = self.renderer.format_live_metrics(self.task_id, self.metrics)
        block = f"{output_line}\n{status_line}  [{metrics_text}]"
        if block == self._last_live_block:
            return
        self._last_live_block = block
        self._has_live_status = True
        # Overwrite the last two lines in-place.
        sys.stdout.write("\r\x1b[2K" + output_line + "\n" + "\r\x1b[2K" + status_line + "  [" + metrics_text + "]\x1b[1A\r")
        sys.stdout.flush()

    def set_system_note(self, note: str) -> None:
        self.metrics.last_note = note
        self.metrics.last_note_time = time.time()

    def _update_ui_state(self, lines: List[str]) -> None:
        continue_lines = 0
        has_review_hint = False
        has_sessions_menu = False
        has_followup_prompt = False
        has_empty_prompt = False
        for raw in lines:
            line = strip_ansi(raw).strip()
            if not line:
                continue
            lower = line.lower()
            if "add a follow-up" in lower:
                has_followup_prompt = True
            if "sessions and cloud agents" in lower:
                has_sessions_menu = True
            if "ctrl+r to review edits" in lower:
                has_review_hint = True
            if line.startswith("→"):
                stripped = line.lstrip("→").strip()
                if not stripped:
                    has_empty_prompt = True
                line = stripped
            if line == "continue":
                continue_lines += 1
        self.ui_prompt_continue_lines = continue_lines
        self.ui_has_review_hint = has_review_hint
        self.ui_sessions_menu = has_sessions_menu
        self.ui_followup_prompt = has_followup_prompt
        self.ui_empty_prompt = has_empty_prompt

    def _normalize_key(self, key: str) -> str:
        raw = key.strip()
        lower = raw.lower()
        if lower.startswith("ctrl+"):
            raw = "C-" + raw[5:]
            lower = raw.lower()
        if lower.startswith("ctrl-"):
            raw = "C-" + raw[5:]
            lower = raw.lower()
        if lower.startswith("c-"):
            rest = raw[2:]
            if rest.lower() == "enter":
                rest = "Enter"
            elif rest.lower() == "m":
                rest = "m"
            return "C-" + rest
        if lower == "enter":
            return "Enter"
        return raw

    def _normalize_keys(self, keys: List[str]) -> List[str]:
        return [self._normalize_key(key) for key in keys]

    def send_keys(self, keys: List[str], label: str = "", fallback: Optional[List[List[str]]] = None) -> bool:
        attempts = [keys]
        if fallback:
            attempts.extend(fallback)
        for idx, attempt in enumerate(attempts, start=1):
            normalized = self._normalize_keys(attempt)
            payload = {"type": "sendKeys", "keys": normalized}
            ok = self.send_command(payload)
            log_event(
                self.log_path,
                "INFO" if ok else "WARN",
                "ht sendKeys",
                keys=normalized,
                label=label,
                attempt=idx,
            )
            if ok:
                return True
        return False

    def update_git_stats(self) -> None:
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat"],
                cwd=self.workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except Exception:
            return
        if result.returncode != 0:
            return
        added = 0
        deleted = 0
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            a, d = parts[0], parts[1]
            try:
                added += int(a)
            except ValueError:
                pass
            try:
                deleted += int(d)
            except ValueError:
                pass
        self.metrics.git_added = added
        self.metrics.git_deleted = deleted

    def update_process_stats(self) -> None:
        if not self.init_pid:
            return
        pids = build_process_tree(self.init_pid)
        if not pids:
            return
        try:
            result = subprocess.run(
                ["ps", "-o", "pid=,pcpu=,rss=", "-p", ",".join(str(pid) for pid in pids)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except Exception:
            return
        if result.returncode != 0:
            return
        cpu_total = 0.0
        rss_kb = 0
        count = 0
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            try:
                raw_cpu = parts[1].strip().replace(",", ".")
                if raw_cpu.endswith("%"):
                    raw_cpu = raw_cpu[:-1]
                cpu_total += float(raw_cpu)
            except ValueError:
                pass
            try:
                rss_kb += int(parts[2])
            except ValueError:
                pass
            count += 1
        if count:
            self.metrics.proc_count = count
            self.metrics.proc_cpu = round(cpu_total, 1)
            self.metrics.proc_rss_mb = round(rss_kb / 1024.0, 1)

    def _read_stdout(self) -> None:
        if self.proc.stdout is None:
            return
        for line in self.proc.stdout:
            if self._stop.is_set():
                break
            raw = line.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
                event_type = event.get("type")
                data = event.get("data") or {}
            except Exception as exc:
                log_event(self.log_path, "ERROR", "ht stdout: bad json", error=str(exc), raw=raw[:500])
                continue
            if event_type == "init":
                # Treat init as activity to avoid false stalls early.
                self.last_output_time = time.time()
                pid = data.get("pid")
                if isinstance(pid, int):
                    self.init_pid = pid
                log_event(self.log_path, "INFO", "ht init", pid=self.init_pid, cols=data.get("cols"), rows=data.get("rows"))
                #region agent log
                debug_log(
                    "H1",
                    "orc_core/monitor.py:HtMonitor._read_stdout:init",
                    "ht init event",
                    {"pid": self.init_pid, "cols": data.get("cols"), "rows": data.get("rows")},
                )
                #endregion
            elif event_type == "output":
                self.last_output_time = time.time()
                seq = data.get("seq") or ""
                preview = seq[:200]
                log_event(self.log_path, "INFO", "ht output", length=len(seq), preview=preview)
                self._record_text(seq)
                if not self._debug_first_output_logged:
                    self._debug_first_output_logged = True
                    #region agent log
                    debug_log(
                        "H1",
                        "orc_core/monitor.py:HtMonitor._read_stdout:output",
                        "first output event",
                        {"seq_len": len(seq), "preview": preview},
                    )
                    #endregion
            elif event_type == "snapshot":
                # Snapshots are a sign of liveness (and often carry token updates),
                # so treat them as activity to avoid false "stall" detection.
                self.last_output_time = time.time()
                log_event(self.log_path, "INFO", "ht snapshot", cols=data.get("cols"), rows=data.get("rows"))
                text = data.get("text") or ""
                snapshot_lines = text.splitlines()
                self._last_snapshot_lines = snapshot_lines
                self._update_ui_state(snapshot_lines)
                tokens = extract_tokens_from_text(text)
                if tokens is not None:
                    self.metrics.tokens_total = max(self.metrics.tokens_total or 0, tokens)
                files_edited = extract_files_edited_from_text(text)
                if files_edited is not None:
                    self.metrics.files_edited = max(self.metrics.files_edited or 0, files_edited)
                #region agent log
                debug_log(
                    "H15",
                    "orc_core/monitor.py:HtMonitor._read_stdout:snapshot",
                    "snapshot received",
                    {"lines": len(snapshot_lines), "tokens": self.metrics.tokens_total or 0, "files_edited": self.metrics.files_edited or 0},
                )
                #endregion
                self.update_live_status(snapshot_lines)
            else:
                log_event(self.log_path, "INFO", "ht event", event_type=event_type)

    def _read_stderr(self) -> None:
        if self.proc.stderr is None:
            return
        for line in self.proc.stderr:
            if self._stop.is_set():
                break
            raw = line.strip()
            if not raw:
                continue
            log_event(self.log_path, "WARN", "ht stderr", line=raw[:500])
            self.last_stderr_line = raw[:500]
            self.stderr_count += 1
            if not self._debug_first_stderr_logged:
                self._debug_first_stderr_logged = True
                #region agent log
                debug_log(
                    "H4",
                    "orc_core/monitor.py:HtMonitor._read_stderr",
                    "first stderr line",
                    {"line": self.last_stderr_line},
                )
                #endregion

    def stop(self) -> None:
        self._stop.set()
