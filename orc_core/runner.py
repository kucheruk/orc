#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import shlex
from pathlib import Path
from typing import Callable, Optional

from .logging import debug_log, log_event
from .process import kill_orphan_project_processes, kill_process_tree
from .process_groups import terminate_process_group
from .stream_monitor import StreamJsonMonitor
from .stream_monitor_state import MonitorSnapshot


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
    agent_output_log_path: Optional[str] = None,
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
    resume_id: Optional[str] = None,
    resume_latest: bool = False,
    resume_prompt: Optional[str] = None,
) -> StreamJsonMonitor:
    return asyncio.run(
        launch_agent_stream_json_async(
            workdir=workdir,
            prompt_path=prompt_path,
            model=model,
            log_path=log_path,
            report_interval=report_interval,
            summary_lines=summary_lines,
            task_id=task_id,
            progress_done=progress_done,
            progress_total=progress_total,
            agent_output_log_path=agent_output_log_path,
            snapshot_publisher=snapshot_publisher,
            resume_id=resume_id,
            resume_latest=resume_latest,
            resume_prompt=resume_prompt,
        )
    )


async def launch_agent_stream_json_async(
    *,
    workdir: str,
    prompt_path: Optional[Path],
    model: str,
    log_path: Path,
    report_interval: float,
    summary_lines: int,
    task_id: str,
    progress_done: int = 0,
    progress_total: int = 1,
    agent_output_log_path: Optional[str] = None,
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
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
            "agent_output_log_path": agent_output_log_path,
            "snapshot_publisher": bool(snapshot_publisher),
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
    monitor = StreamJsonMonitor(
        agent_cmd=agent_cmd,
        log_path=log_path,
        report_interval=report_interval,
        summary_lines=summary_lines,
        task_id=task_id,
        workdir=workdir,
        agent_output_log_path=agent_output_log_path,
        snapshot_publisher=snapshot_publisher,
    )
    try:
        monitor.set_progress(progress_done, progress_total)
    except Exception:
        monitor.stop()
        if not terminate_process_group(getattr(monitor, "process_group_id", None), log_path, label="agent-launch"):
            kill_process_tree(monitor.init_pid or monitor.proc.pid, log_path, label="agent-launch")
        kill_orphan_project_processes(
            str(getattr(monitor, "workdir", "") or workdir),
            log_path,
            label="agent-launch-orphan-sweep",
            started_after=getattr(monitor, "started_at", None),
            command_markers=("agent", "orc.py", "pytest", "unittest", "pyenv-which"),
        )
        raise
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_stream_json:spawned",
        "agent spawned",
        {"pid": monitor.proc.pid},
    )
    return monitor
