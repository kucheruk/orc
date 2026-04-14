#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Timing / model / template config bundles for a task run."""

from __future__ import annotations

from dataclasses import dataclass


ETA_WINDOW_SIZE = 20


@dataclass(frozen=True)
class TimingConfig:
    poll: float
    stall_timeout: float
    task_ttl: float
    max_restarts: int
    report_interval: float
    summary_lines: int
    nudge_after: int
    nudge_cooldown: float
    nudge_text: str
    commit_stall_timeout: float
    commit_ttl: float


@dataclass(frozen=True)
class ModelConfig:
    model: str
    commit_model: str
    merge_expert_model: str


@dataclass(frozen=True)
class TemplateConfig:
    prompt_template: str
    continue_template: str
    commit_template: str
    merge_expert_template: str
