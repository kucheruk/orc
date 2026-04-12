#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Typed configuration for ORC runtime — replaces untyped argparse.Namespace."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrcConfig:
    """Typed config extracted from CLI args at the boundary."""

    model: str = ""
    commit_model: str = ""
    commit_phase: bool = True
    poll: float = 0.5
    stall_timeout: float = 300.0
    max_restarts: int = 1
    report_interval: float = 30.0
    summary_lines: int = 5
    nudge_after: int = 0
    nudge_cooldown: float = 120.0
    nudge_text: str = ""
    commit_stall_timeout: float = 120.0
    commit_ttl: float = 300.0
    agent_output_log_path: str = ""

    @classmethod
    def from_namespace(cls, args) -> OrcConfig:
        """Construct from argparse.Namespace, applying defaults for missing attrs."""
        return cls(
            model=str(getattr(args, "model", "") or ""),
            commit_model=str(getattr(args, "commit_model", "") or ""),
            commit_phase=bool(getattr(args, "commit_phase", True)),
            poll=float(getattr(args, "poll", 0.5)),
            stall_timeout=float(getattr(args, "stall_timeout", 300.0)),
            max_restarts=int(getattr(args, "max_restarts", 1)),
            report_interval=float(getattr(args, "report_interval", 30.0)),
            summary_lines=int(getattr(args, "summary_lines", 5)),
            nudge_after=int(getattr(args, "nudge_after", 0)),
            nudge_cooldown=float(getattr(args, "nudge_cooldown", 120.0)),
            nudge_text=str(getattr(args, "nudge_text", "")),
            commit_stall_timeout=float(getattr(args, "commit_stall_timeout", 120.0)),
            commit_ttl=float(getattr(args, "commit_ttl", 300.0)),
            agent_output_log_path=str(getattr(args, "agent_output_log_path", "") or ""),
        )
