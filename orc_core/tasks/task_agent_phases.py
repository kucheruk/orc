#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent sub-phase execution: commit phase, merge expert, process cleanup.

Extracted from task_execution.py to reduce its size and isolate the
agent lifecycle (launch → wait → cleanup → check) from the main
task execution engine.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..git.git_helpers import (
    attempt_autocommit_fallback as _attempt_autocommit_fallback,
    git_status_porcelain as _git_status_porcelain,
    parse_git_porcelain as _parse_git_porcelain,
    runtime_artifact_paths_from_porcelain_lines as _runtime_artifact_paths_from_porcelain_lines,
)
from .execution.request import LaunchConfig
from ..models.task_status import TaskCompletionStatus, TaskExecutionStatus
from ..log import log_event
from ..infra.monitoring.monitor_protocol import StreamMonitorProtocol
from ..infra.io.timeline import timeline_step
from ..infra.process.process import (
    ORPHAN_SWEEP_COMMAND_MARKERS,
    build_process_tree,
    is_pid_alive,
    kill_orphan_project_processes,
    kill_process_tree,
)
from ..infra.process.process_groups import terminate_process_group
from ..quit_signal import is_stop_requested
from ..supervision.lifecycle import wait_for_process_exit
from .execution.helpers import _write_prompt_file
from .execution.request import TaskExecutionRequest, TaskExecutionResult
from .execution.stage import AgentPhaseSpec
from .execution.worker import TaskWorker
from ..text_parse import SafeDict

_logger = logging.getLogger(__name__)


def cleanup_monitor_processes(monitor: StreamMonitorProtocol, log_path: Path, label: str) -> None:
    """Kill agent process tree and sweep orphan processes."""
    root_pid = monitor.init_pid or monitor.proc.pid
    process_group_id = monitor.process_group_id
    workspace = monitor.workdir or ""
    started_at = monitor.started_at
    run_token = monitor.run_token or None
    if terminate_process_group(process_group_id, log_path, label=label):
        if isinstance(root_pid, int) and root_pid > 0 and is_pid_alive(root_pid):
            lingering = build_process_tree(root_pid)
            if lingering:
                log_event(
                    log_path,
                    "WARN",
                    "cleanup post-check: lingering process tree",
                    label=label,
                    root_pid=root_pid,
                    pids=lingering,
                )
                kill_process_tree(root_pid, log_path, label=f"{label}-postcheck")
        kill_orphan_project_processes(
            workspace,
            log_path,
            label=f"{label}-orphan-sweep",
            started_after=started_at,
            command_markers=ORPHAN_SWEEP_COMMAND_MARKERS,
            run_token=run_token,
        )
        return
    kill_process_tree(root_pid, log_path, label=label)
    kill_orphan_project_processes(
        workspace,
        log_path,
        label=f"{label}-orphan-sweep",
        started_after=started_at,
        command_markers=ORPHAN_SWEEP_COMMAND_MARKERS,
        run_token=run_token,
    )


def run_agent_phase(
    *,
    worker: TaskWorker,
    request: TaskExecutionRequest,
    phase: AgentPhaseSpec,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
    timeline_id: str,
    attempt: int,
) -> bool:
    """Common skeleton for agent sub-phases: format → launch → wait → cleanup → check."""
    with timeline_step(
        timeline_id=timeline_id, task_id=task_id,
        step=phase.step_name,
        location=f"orc_core/task_agent_phases.py:run_agent_phase({phase.step_name})",
        attempt=attempt, data={"model": phase.model},
    ) as ts:
        prompt = phase.template.format_map(prompt_vars)
        prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}{phase.tag_suffix}")
        log_event(log_path, "INFO", f"{phase.label} starting",
                  task_id=task_id, prompt_path=str(prompt_path), model=phase.model)
        _logger.info(f"[orc] {phase.label}: starting")

        try:
            monitor = worker.launch(LaunchConfig(
                workdir=phase.workdir,
                prompt_path=prompt_path,
                model=phase.model,
                log_path=log_path,
                report_interval=15.0,
                summary_lines=25,
                task_id=f"{task_id}{phase.task_id_suffix}",
                progress_done=request.progress_done,
                progress_total=request.progress_total,
                agent_output_log_path=agent_output_log_path,
                agent_env=request.agent_env,
                snapshot_publisher=request.snapshot_publisher,
                timeline_id=timeline_id,
                attempt=attempt,
            ))
        except Exception as exc:
            log_event(log_path, "ERROR", f"{phase.label} launch failed", task_id=task_id, error=str(exc))
            _logger.error(f"[orc] {phase.label}: launch failed ({type(exc).__name__})")
            ts.result = "failed"
            ts.reason = "launch_failed"
            ts.finish_data = {"error": str(exc)}
            return False

        try:
            result = wait_for_process_exit(
                monitor=monitor,
                poll=request.timing.poll,
                stall_timeout=phase.stall_timeout,
                task_ttl=phase.ttl,
                log_path=log_path,
                label=phase.step_name,
                stop_on_followup_prompt=True,
                timeline_id=timeline_id,
                task_id=task_id,
                attempt=attempt,
                escape_requested=is_stop_requested,
            )
        finally:
            try:
                monitor.stop()
            except Exception:
                pass
            cleanup_monitor_processes(monitor, log_path, label=phase.label.replace(" ", "-"))

        if result != TaskCompletionStatus.COMPLETED:
            log_event(log_path, "ERROR", f"{phase.label} failed", task_id=task_id, result=result)
            _logger.error(f"[orc] {phase.label}: failed ({result})")
            ts.result = "failed"
            ts.reason = result
            return False

        log_event(log_path, "INFO", f"{phase.label} completed", task_id=task_id)
        _logger.info(f"[orc] {phase.label}: completed")
        return True


def commit_phase_spec(request: TaskExecutionRequest) -> AgentPhaseSpec:
    """Build spec for the commit agent phase."""
    return AgentPhaseSpec(
        step_name="commit_phase",
        label="commit phase",
        model=request.models.commit_model,
        template=request.templates.commit_template,
        workdir=request.workdir,
        tag_suffix="__commit",
        task_id_suffix="::commit",
        stall_timeout=request.timing.commit_stall_timeout,
        ttl=request.timing.commit_ttl,
    )


def merge_expert_phase_spec(request: TaskExecutionRequest) -> AgentPhaseSpec:
    """Build spec for the merge expert agent phase."""
    return AgentPhaseSpec(
        step_name="merge_expert_phase",
        label="merge expert phase",
        model=request.models.merge_expert_model,
        template=request.templates.merge_expert_template,
        workdir=request.base_workdir,
        tag_suffix="__merge_expert",
        task_id_suffix="::merge-expert",
        stall_timeout=request.timing.commit_stall_timeout,
        ttl=request.timing.commit_ttl,
    )


def run_commit_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
    timeline_id: str,
    attempt: int,
) -> bool:
    """Run commit phase: pre-check → agent → post-check with fallback."""
    # Pre-check: skip if tree is clean
    ok, porcelain = _git_status_porcelain(request.workdir, log_path)
    if ok and not porcelain.strip():
        log_event(log_path, "INFO", "commit phase skipped: clean tree", task_id=task_id)
        _logger.info("[orc] commit phase: skip (clean tree)")
        return True

    phase_ok = run_agent_phase(
        worker=worker, request=request, phase=commit_phase_spec(request),
        prompt_vars=prompt_vars, task_id=task_id, tag=tag, log_path=log_path,
        agent_output_log_path=agent_output_log_path, timeline_id=timeline_id, attempt=attempt,
    )
    if not phase_ok:
        return False

    # Post-check: verify git tree is clean after commit
    ok2, porcelain2 = _git_status_porcelain(request.workdir, log_path)
    if ok2 and porcelain2.strip():
        tracked, untracked = _parse_git_porcelain(porcelain2)
        runtime_tracked, non_runtime_tracked = _runtime_artifact_paths_from_porcelain_lines(tracked)
        runtime_untracked, non_runtime_untracked = _runtime_artifact_paths_from_porcelain_lines(untracked)
        if runtime_tracked or runtime_untracked:
            log_event(
                log_path, "WARN",
                "commit phase: ignoring runtime artifacts in git status",
                task_id=task_id,
                tracked_runtime=len(runtime_tracked),
                untracked_runtime=len(runtime_untracked),
            )
        tracked = non_runtime_tracked
        untracked = non_runtime_untracked
        log_event(
            log_path, "WARN", "commit phase left dirty tree",
            task_id=task_id, tracked=len(tracked),
            untracked=len(untracked), porcelain=porcelain2[:500],
        )
        if not tracked and untracked:
            _logger.warning("[orc] commit phase: warning (repo has untracked files)")
            return True

        if tracked:
            task_text = str(prompt_vars.get("task_text") or "").strip()
            if request.allow_fallback_commits:
                _logger.warning("[orc] commit phase: tracked changes remain; attempting fallback commit")
                if not _attempt_autocommit_fallback(request.workdir, log_path, task_id=task_id, task_text=task_text):
                    _logger.error("[orc] commit phase: fallback commit failed")
                    return False

                ok3, porcelain3 = _git_status_porcelain(request.workdir, log_path)
                if ok3 and porcelain3.strip():
                    tracked3, untracked3 = _parse_git_porcelain(porcelain3)
                    if tracked3:
                        log_event(
                            log_path, "ERROR",
                            "commit phase still dirty after fallback",
                            task_id=task_id, tracked=len(tracked3),
                            untracked=len(untracked3), porcelain=porcelain3[:500],
                        )
                        _logger.error("[orc] commit phase: still dirty after fallback")
                        return False
                    _logger.warning("[orc] commit phase: completed (untracked leftovers remain)")
                    return True
                log_event(log_path, "INFO", "commit phase completed after fallback", task_id=task_id)
                _logger.info("[orc] commit phase: completed")
                return True

            log_event(
                log_path, "ERROR",
                "commit phase failed: tracked changes remain and fallback disabled",
                task_id=task_id, tracked=len(tracked),
                untracked=len(untracked), porcelain=porcelain2[:500],
            )
            _logger.error("[orc] commit phase: completed but tracked changes remain (fallback disabled)")
            return False
        _logger.warning("[orc] commit phase: completed (untracked leftovers remain)")
        return True

    return True


def run_merge_expert_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
    timeline_id: str,
    attempt: int,
) -> bool:
    """Run merge expert agent phase."""
    return run_agent_phase(
        worker=worker, request=request, phase=merge_expert_phase_spec(request),
        prompt_vars=prompt_vars, task_id=task_id, tag=tag, log_path=log_path,
        agent_output_log_path=agent_output_log_path, timeline_id=timeline_id, attempt=attempt,
    )


def should_retry_after_missing_stage_artifact(
    *,
    stage_failure: TaskExecutionResult,
    monitor_result: str,
    current_stage_id: str,
    retry_budget_left: int,
) -> bool:
    """Check if a stage should be retried after missing artifact."""
    if retry_budget_left <= 0:
        return False
    if monitor_result != TaskCompletionStatus.PROCESS_EXITED:
        return False
    if stage_failure.status != TaskExecutionStatus.FAILED:
        return False
    return stage_failure.reason.startswith(f"stage_artifact_{current_stage_id}_")
