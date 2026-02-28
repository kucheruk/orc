#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shlex
import subprocess
from pathlib import Path
from typing import Optional

from .logging import debug_log, log_event
from .stream_monitor import StreamJsonMonitor


def launch_agent_stream_json(
    workdir: str,
    prompt_path: Optional[Path],
    model: str,
    log_path: Path,
    report_interval: float,
    summary_lines: int,
    task_id: str,
    progress_done: int = 0,
    progress_total: int = 1,
    resume_id: Optional[str] = None,
    resume_latest: bool = False,
    resume_prompt: Optional[str] = None,
) -> StreamJsonMonitor:
    #region agent log
    debug_log(
        "H2",
        "orc_core/runner.py:launch_agent_stream_json",
        "launch agent stream-json",
        {
            "workdir": workdir,
            "prompt_path": str(prompt_path) if prompt_path else None,
            "model": model,
            "progress_done": progress_done,
            "progress_total": progress_total,
            "resume_id": resume_id,
            "resume_latest": resume_latest,
            "resume_prompt": resume_prompt,
        },
    )
    #endregion

    agent_cmd = [
        "agent",
        "-p",
        "--force",
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--stream-partial-output",
    ]
    if resume_id:
        agent_cmd.extend(["--resume", resume_id])
        if resume_prompt:
            agent_cmd.append(resume_prompt)
    elif resume_latest:
        agent_cmd.append("--continue")
        if resume_prompt:
            agent_cmd.append(resume_prompt)
    else:
        if prompt_path is None:
            raise ValueError("prompt_path is required when not resuming")
        prompt = prompt_path.read_text(encoding="utf-8")
        agent_cmd.append(prompt)
    #region agent log
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_stream_json:cmd",
        "agent command",
        {"cmd": " ".join(shlex.quote(part) for part in agent_cmd)},
    )
    #endregion
    log_event(log_path, "INFO", "launch agent stream-json", command=" ".join(shlex.quote(part) for part in agent_cmd))
    try:
        proc = subprocess.Popen(
            agent_cmd,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        log_event(log_path, "ERROR", "agent executable not found", error=str(exc))
        raise
    #region agent log
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_stream_json:spawned",
        "agent spawned",
        {"pid": proc.pid},
    )
    #endregion
    monitor = StreamJsonMonitor(
        proc,
        log_path,
        report_interval=report_interval,
        summary_lines=summary_lines,
        task_id=task_id,
        workdir=workdir,
    )
    monitor.set_progress(progress_done, progress_total)
    return monitor
