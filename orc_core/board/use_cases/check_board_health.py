#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: detect board health issues (deadlocks, starvation).

Pure domain logic — no agent invocation, no I/O. Returns a diagnostic
or None if the board is healthy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from ..kanban_board_health import CircularDependencyDiagnostic, detect_circular_deps
from ..stage_constants import STAGE_DONE


class BoardInspector(Protocol):
    """Port for board health inspection."""
    def detect_wip_deadlock(self) -> str: ...
    @property
    def cards(self) -> list: ...


class WorkDistributor(Protocol):
    """Port for work distribution diagnostics."""
    def has_remaining_work(self) -> bool: ...
    def diagnose_no_work(self) -> str: ...


@dataclass(frozen=True)
class HealthDiagnostic:
    """Result of a board health check."""
    deadlock: str = ""
    starvation: str = ""
    cycle_nodes: tuple[str, ...] = ()
    cycle_edges: tuple[tuple[str, str], ...] = ()

    @property
    def has_issues(self) -> bool:
        return bool(self.deadlock or self.starvation)

    @property
    def summary(self) -> str:
        parts = []
        if self.deadlock:
            parts.append(f"DEADLOCK: {self.deadlock}")
        if self.starvation:
            parts.append(f"STARVATION: {self.starvation}")
        return "\n".join(parts)

    @property
    def is_dependency_only_starvation(self) -> bool:
        """True if starvation is caused entirely by unmet deps / blocked cards."""
        if not self.starvation or self.deadlock:
            return False
        return all(
            "unmet deps" in line or "action=Blocked" in line
            or "no matching role" in line
            for line in self.starvation.split(";") if line.strip()
        )

    @property
    def has_cycle(self) -> bool:
        return bool(self.cycle_nodes and self.cycle_edges)


def diagnose_board_health(
    board: BoardInspector,
    distributor: WorkDistributor,
) -> Optional[HealthDiagnostic]:
    """Check board for deadlocks and starvation.

    Returns HealthDiagnostic if issues found, None if board is healthy.
    """
    deadlock = board.detect_wip_deadlock()
    circular: CircularDependencyDiagnostic | None = None
    try:
        active_cards = [c for c in board.cards if getattr(c, "stage", "") != STAGE_DONE]
        done_ids = {c.id for c in board.cards if getattr(c, "stage", "") == STAGE_DONE}
        circular = detect_circular_deps(active_cards, done_ids)
    except Exception:
        circular = None
    starvation = ""
    if not deadlock:
        if distributor.has_remaining_work():
            diag = distributor.diagnose_no_work()
            if diag and "board empty" not in diag:
                starvation = diag

    if not deadlock and not starvation and not circular:
        return None

    diagnostic = HealthDiagnostic(
        deadlock=deadlock or (circular.summary if circular else ""),
        starvation=starvation,
        cycle_nodes=circular.cycle_nodes if circular else (),
        cycle_edges=circular.cycle_edges if circular else (),
    )

    # Dependency-only starvation doesn't need AI intervention
    if diagnostic.is_dependency_only_starvation:
        return None

    return diagnostic


def should_skip_repeated_diagnostic(
    diagnostic: HealthDiagnostic,
    last_diagnostic_summary: str,
    consecutive_checks: int,
) -> bool:
    """Returns True if we've already seen this exact diagnostic."""
    return (
        diagnostic.summary == last_diagnostic_summary
        and consecutive_checks > 0
    )
