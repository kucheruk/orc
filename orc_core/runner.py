#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shlex
import subprocess
from pathlib import Path
from typing import Optional

from .logging import debug_log, log_event
from .monitor import HtMonitor


def launch_agent_with_ht(
    workdir: str,
    prompt_path: Optional[Path],
    model: str,
    log_path: Path,
    report_interval: float,
    summary_lines: int,
    listen_addr: str,
    task_id: str,
    resume_id: Optional[str] = None,
    resume_latest: bool = False,
    resume_prompt: Optional[str] = None,
) -> HtMonitor:
    #region agent log
    debug_log(
        "H2",
        "orc_core/runner.py:launch_agent_with_ht",
        "launch ht",
        {
            "workdir": workdir,
            "prompt_path": str(prompt_path) if prompt_path else None,
            "model": model,
            "resume_id": resume_id,
            "resume_latest": resume_latest,
            "resume_prompt": resume_prompt,
        },
    )
    #endregion
    ht_cmd = [
        "ht",
        "--subscribe",
        "init,output,snapshot",
        "--size",
        "120x40",
    ]
    if listen_addr:
        ht_cmd.extend(["--listen", listen_addr])
    resume_prompt_arg = f" {shlex.quote(resume_prompt)}" if resume_prompt else ""
    if resume_id:
        ht_cmd.extend(
            [
                "--",
                "bash",
                "-lc",
                f"cd {shlex.quote(workdir)} && agent --force --model {shlex.quote(model)} --resume {shlex.quote(resume_id)}{resume_prompt_arg}",
            ]
        )
    elif resume_latest:
        ht_cmd.extend(
            [
                "--",
                "bash",
                "-lc",
                f"cd {shlex.quote(workdir)} && agent --force --model {shlex.quote(model)} --resume{resume_prompt_arg}",
            ]
        )
    else:
        if prompt_path is None:
            raise ValueError("prompt_path is required when not resuming")
        ht_cmd.extend(
            [
                "--",
                "bash",
                "-lc",
                f"cd {shlex.quote(workdir)} && agent --force --model {shlex.quote(model)} \"$(cat {shlex.quote(str(prompt_path))})\"",
            ]
        )
    #region agent log
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_with_ht:cmd",
        "ht command",
        {"cmd": " ".join(ht_cmd)},
    )
    #endregion
    log_event(log_path, "INFO", "launch ht", command=" ".join(ht_cmd))
    try:
        proc = subprocess.Popen(
            ht_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        log_event(log_path, "ERROR", "ht executable not found", error=str(exc))
        raise
    #region agent log
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_with_ht:spawned",
        "ht spawned",
        {"pid": proc.pid},
    )
    #endregion
    return HtMonitor(
        proc,
        log_path,
        report_interval=report_interval,
        summary_lines=summary_lines,
        task_id=task_id,
        workdir=workdir,
    )
