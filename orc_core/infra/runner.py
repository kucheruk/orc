#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping, Optional

from .io.logging import log_event, now_ms
from .io.debug_log import debug_log
from .io.timeline import timeline_instant
from .process.process import ORPHAN_SWEEP_COMMAND_MARKERS, kill_orphan_project_processes, kill_process_tree
from .process.process_groups import terminate_process_group
from .monitoring.stream_monitor import StreamJsonMonitor
from ..infra.monitoring.monitor_dto import MonitorSnapshot

if TYPE_CHECKING:
    from .backend import Backend


def launch_agent_stream_json(
    workdir: str,
    prompt_path: Optional[Path],
    model: str,
    log_path: Path,
    report_interval: float,
    summary_lines: int,
    task_id: str,
    backend: "Backend",
    progress_done: int = 0,
    progress_total: int = 1,
    progress_in_progress: int = 0,
    agent_output_log_path: Optional[str] = None,
    agent_env: Optional[Mapping[str, str]] = None,
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
    resume_id: Optional[str] = None,
    resume_latest: bool = False,
    resume_prompt: Optional[str] = None,
    timeline_id: str = "",
    attempt: int = 0,
    backlog_task_lister: Optional[Callable] = None,
    git_diff_fn: Optional[Callable] = None,
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
            progress_in_progress=progress_in_progress,
            agent_output_log_path=agent_output_log_path,
            agent_env=agent_env,
            snapshot_publisher=snapshot_publisher,
            resume_id=resume_id,
            resume_latest=resume_latest,
            resume_prompt=resume_prompt,
            timeline_id=timeline_id,
            attempt=attempt,
            backend=backend,
            backlog_task_lister=backlog_task_lister,
            git_diff_fn=git_diff_fn,
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
    backend: "Backend",
    progress_done: int = 0,
    progress_total: int = 1,
    progress_in_progress: int = 0,
    agent_output_log_path: Optional[str] = None,
    agent_env: Optional[Mapping[str, str]] = None,
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
    resume_id: Optional[str] = None,
    resume_latest: bool = False,
    resume_prompt: Optional[str] = None,
    timeline_id: str = "",
    attempt: int = 0,
    backlog_task_lister: Optional[Callable] = None,
    git_diff_fn: Optional[Callable] = None,
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
            "agent_env": dict(agent_env or {}),
            "snapshot_publisher": bool(snapshot_publisher),
            "resume_id": resume_id,
            "resume_latest": resume_latest,
            "resume_prompt": resume_prompt,
            "timeline_id": timeline_id,
            "attempt": attempt,
        },
    )
    #endregion

    prompt_text: str | None = None
    if not resume_id and not resume_latest:
        if prompt_path is None:
            raise ValueError("prompt_path is required when not resuming")
        prompt_text = prompt_path.read_text(encoding="utf-8")

    agent_cmd = backend.build_agent_cmd(
        model=model,
        prompt=prompt_text,
        resume_id=resume_id,
        resume_latest=resume_latest,
        resume_prompt=resume_prompt,
    )
    #region agent log
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_stream_json:cmd",
        "agent command",
        {"cmd": " ".join(shlex.quote(part) for part in agent_cmd)},
    )
    #endregion
    log_event(log_path, "INFO", "launch agent stream-json", command=" ".join(shlex.quote(part) for part in agent_cmd))
    spawn_started_ms = now_ms()
    monitor = StreamJsonMonitor(
        agent_cmd=agent_cmd,
        log_path=log_path,
        report_interval=report_interval,
        summary_lines=summary_lines,
        task_id=task_id,
        workdir=workdir,
        agent_output_log_path=agent_output_log_path,
        child_env_overrides=dict(agent_env or {}),
        snapshot_publisher=snapshot_publisher,
        timeline_id=timeline_id,
        attempt=attempt,
        backlog_task_lister=backlog_task_lister,
        git_diff_fn=git_diff_fn,
    )
    try:
        monitor.set_progress(progress_done, progress_total, progress_in_progress)
    except Exception:
        monitor.stop()
        if not terminate_process_group(monitor.process_group_id, log_path, label="agent-launch"):
            kill_process_tree(monitor.init_pid or monitor.proc.pid, log_path, label="agent-launch")
        kill_orphan_project_processes(
            monitor.workdir or workdir,
            log_path,
            label="agent-launch-orphan-sweep",
            started_after=monitor.started_at,
            command_markers=ORPHAN_SWEEP_COMMAND_MARKERS,
            run_token=monitor.run_token or None,
        )
        raise
    debug_log(
        "H1",
        "orc_core/runner.py:launch_agent_stream_json:spawned",
        "agent spawned",
        {"pid": monitor.proc.pid},
    )
    timeline_instant(
        timeline_id=timeline_id,
        task_id=task_id,
        step="agent_spawn",
        location="orc_core/runner.py:launch_agent_stream_json_async",
        attempt=attempt,
        result="spawned",
        data={"duration_ms": max(now_ms() - spawn_started_ms, 0), "pid": monitor.proc.pid},
    )
    return monitor
