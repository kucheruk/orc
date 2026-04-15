#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frozen dataclasses for kanban board TUI snapshots and journal events."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .stage_constants import STAGES, STAGE_DONE

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard
    from ..infra.monitoring.monitor_dto import MonitorSnapshot


@dataclass(frozen=True)
class CardSnapshot:
    id: str
    title: str
    stage: str
    action: str
    class_of_service: str
    assigned_agent: str
    value_score: int
    effort_score: int
    roi: float
    loop_count: int
    created_at: str
    updated_at: str
    input_bytes: int = 0
    output_bytes: int = 0
    elapsed_seconds: float = 0.0
    live_phase: str = ""


@dataclass(frozen=True)
class StageSnapshot:
    name: str
    cards: tuple[CardSnapshot, ...]
    count: int
    wip_limit: int


@dataclass(frozen=True)
class BoardMetrics:
    avg_lead_time_minutes: float
    throughput_per_hour: float
    total_cards: int
    done_cards: int
    blocked_cards: int


@dataclass(frozen=True)
class KanbanBoardSnapshot:
    stages: tuple[StageSnapshot, ...]
    metrics: BoardMetrics
    timestamp: float


@dataclass(frozen=True)
class JournalEntry:
    timestamp: float
    category: str  # move, action, assign, roi, complete, escalate, inbox, split, arbitration
    card_id: str
    message: str

    def format_line(self) -> str:
        t = datetime.fromtimestamp(self.timestamp, tz=timezone.utc).strftime("%H:%M:%S")
        return f"[dim]{t}[/dim] [bold][{_CAT_COLOR.get(self.category, 'white')}]{self.category:10s}[/{_CAT_COLOR.get(self.category, 'white')}][/bold] {self.message}"


_CAT_COLOR: dict[str, str] = {
    "move": "cyan",
    "action": "bright_cyan",
    "assign": "bright_blue",
    "user": "white",
    "system": "dim",
    "roi": "yellow",
    "complete": "green",
    "escalate": "red",
    "approval": "yellow",
    "inbox": "blue",
    "split": "magenta",
    "arbitration": "red",
    "teamlead": "bright_magenta",
    "directive": "bright_yellow",
}


def build_board_snapshot(
    board: "KanbanBoard",
    session_snapshots: dict[str, "MonitorSnapshot"],
    started_at: float = 0.0,
) -> KanbanBoardSnapshot:
    now = time.time()
    agent_to_snap: dict[str, "MonitorSnapshot"] = {}
    for sid, snap in session_snapshots.items():
        agent_to_snap[sid] = snap

    stages: list[StageSnapshot] = []
    total = 0
    done_count = 0
    blocked_count = 0

    for stage_name in STAGES:
        cards_in_stage = board.cards_in_stage(stage_name)
        card_snaps: list[CardSnapshot] = []
        for c in cards_in_stage:
            agent_snap = agent_to_snap.get(c.assigned_agent) if c.assigned_agent else None
            elapsed = 0.0
            if agent_snap and agent_snap.started_at > 0:
                elapsed = now - agent_snap.started_at
            card_snaps.append(CardSnapshot(
                id=c.id, title=c.title, stage=c.stage, action=c.action,
                class_of_service=c.class_of_service, assigned_agent=c.assigned_agent,
                value_score=c.value_score, effort_score=c.effort_score, roi=c.roi,
                loop_count=c.loop_count, created_at=c.created_at, updated_at=c.updated_at,
                input_bytes=agent_snap.metrics.input_bytes if agent_snap else 0,
                output_bytes=agent_snap.metrics.output_bytes if agent_snap else 0,
                elapsed_seconds=elapsed,
                live_phase=agent_snap.live_phase if agent_snap else "",
            ))
        count = len(cards_in_stage)
        total += count
        if stage_name == STAGE_DONE:
            done_count = count
        blocked_count += sum(1 for c in cards_in_stage if c.action == "Blocked")
        stages.append(StageSnapshot(
            name=stage_name,
            cards=tuple(card_snaps),
            count=count,
            wip_limit=board.wip_limit(stage_name),
        ))

    lead_time = _compute_avg_lead_time(board)
    hours_elapsed = (now - started_at) / 3600.0 if started_at > 0 else 0.0
    throughput = done_count / hours_elapsed if hours_elapsed > 0.01 else 0.0

    return KanbanBoardSnapshot(
        stages=tuple(stages),
        metrics=BoardMetrics(
            avg_lead_time_minutes=lead_time,
            throughput_per_hour=round(throughput, 1),
            total_cards=total,
            done_cards=done_count,
            blocked_cards=blocked_count,
        ),
        timestamp=now,
    )


def _compute_avg_lead_time(board: "KanbanBoard") -> float:
    done = board.cards_in_stage(STAGE_DONE)
    if not done:
        return 0.0
    total_minutes = 0.0
    count = 0
    for c in done:
        if c.created_at and c.updated_at:
            try:
                created = datetime.fromisoformat(c.created_at)
                updated = datetime.fromisoformat(c.updated_at)
                delta = (updated - created).total_seconds() / 60.0
                if delta > 0:
                    total_minutes += delta
                    count += 1
            except (ValueError, TypeError):
                continue
    return round(total_minutes / count, 1) if count > 0 else 0.0
