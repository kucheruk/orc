#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Typed configuration for ORC runtime — replaces untyped argparse.Namespace."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MODEL = "gpt-5.3-codex"


@dataclass(frozen=True)
class OrcConfig:
    """Typed config extracted from CLI args at the boundary.

    Dataclass defaults are the SSOT — cli_app.py argparse must use them.
    """

    model: str = ""
    commit_model: str = ""
    commit_phase: bool = True
    poll: float = 1.0
    stall_timeout: float = 600.0
    max_restarts: int = 2
    report_interval: float = 2.0
    summary_lines: int = 25
    nudge_after: int = 10
    nudge_cooldown: float = 300.0
    nudge_text: str = "continue"
    commit_stall_timeout: float = 300.0
    commit_ttl: float = 1800.0
    # Per-attempt wall-clock ceiling. 30 min cut real cards off mid-work
    # (PERF-001 profiling project-by-project dotnet test runs routinely
    # needs ~12 min of test wall time plus LLM-think time, AUDIT-001-C
    # accumulated ~20 min of code work). 1 hour is the new baseline —
    # still bounded, still catches runaways, but fits realistic .NET
    # solution test cycles plus a real retry budget.
    task_ttl: float = 3600.0
    agent_output_log_path: str = ""

    @classmethod
    def from_namespace(cls, args) -> OrcConfig:
        """Construct from argparse.Namespace — missing attrs fall back to dataclass defaults."""
        defaults = cls()
        return cls(
            model=str(getattr(args, "model", defaults.model) or ""),
            commit_model=str(getattr(args, "commit_model", defaults.commit_model) or ""),
            commit_phase=bool(getattr(args, "commit_phase", defaults.commit_phase)),
            poll=float(getattr(args, "poll", defaults.poll)),
            stall_timeout=float(getattr(args, "stall_timeout", defaults.stall_timeout)),
            max_restarts=int(getattr(args, "max_restarts", defaults.max_restarts)),
            report_interval=float(getattr(args, "report_interval", defaults.report_interval)),
            summary_lines=int(getattr(args, "summary_lines", defaults.summary_lines)),
            nudge_after=int(getattr(args, "nudge_after", defaults.nudge_after)),
            nudge_cooldown=float(getattr(args, "nudge_cooldown", defaults.nudge_cooldown)),
            nudge_text=str(getattr(args, "nudge_text", defaults.nudge_text)),
            commit_stall_timeout=float(getattr(args, "commit_stall_timeout", defaults.commit_stall_timeout)),
            commit_ttl=float(getattr(args, "commit_ttl", defaults.commit_ttl)),
            task_ttl=float(getattr(args, "task_ttl", defaults.task_ttl)),
            agent_output_log_path=str(getattr(args, "agent_output_log_path", defaults.agent_output_log_path) or ""),
        )
