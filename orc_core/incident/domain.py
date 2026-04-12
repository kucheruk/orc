#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead incident response: data types, prompt builder, decision parser."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml

if TYPE_CHECKING:
    from ..board.kanban_board import KanbanBoard
    from ..board.kanban_card import KanbanCard

# ── Constants ──────────────────────────────────────────────────────

INCIDENT_FIX_TIMEOUT = 600.0       # 10 min for fix agent to complete
SCALE_DOWN_WAIT_TIMEOUT = 60.0     # 1 min for workers to stop
DECISION_FILENAME = "incident-decision.md"

FIX_CARD_PREFIX = "FIX-"


# ── Enums & Data ──────────────────────────────────────────────────

class IncidentPhase(StrEnum):
    SCALE_DOWN = "scale_down"
    TRIAGE = "triage"
    INJECT_FIX = "inject_fix"
    WAIT_FOR_FIX = "wait_for_fix"
    SCALE_UP = "scale_up"
    NOTIFY_HUMAN = "notify_human"


@dataclass
class Incident:
    id: str
    phase: IncidentPhase
    error_type: str                   # worker_crash | agent_failure | validation | integration
    source_task_id: str               # card being processed when error occurred
    source_slot_id: str               # worker that crashed / failed
    error_message: str
    traceback: str
    worktree_path: str = ""           # worktree where the worker was operating
    # Filled after AI triage:
    error_class: str = ""             # project | orc
    target_role: str = ""             # coder | architect | reviewer | integrator
    fix_title: str = ""
    fix_body: str = ""                # fix card body (project) or telegram message (orc)
    # Filled during response:
    fix_card_id: str = ""
    original_worker_count: int = 0
    removed_session_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    fix_started_at: float = 0.0


# ── Prompt builder ────────────────────────────────────────────────

from ..board.kanban_role_registry import ROLE_TEAMLEAD_TRIAGE

_FRONT_RE = re.compile(r"\A---\n(.*?\n?)---\n?(.*)", re.DOTALL)


TRACEBACK_FILENAME = "incident-traceback.txt"


def build_incident_prompt(
    incident: Incident,
    board: "KanbanBoard",
    source_card: Optional["KanbanCard"],
    decision_path: str,
    orc_root: Path,
) -> str:
    """Build the triage prompt with incident context injected.

    Writes the full traceback to a file at ``orc_root / TRACEBACK_FILENAME``
    so the agent can read the untruncated version.
    """
    from ..board.kanban_role_registry import load_role_template
    from ..board.board_summary import format_board_summary
    from ..text_parse import SafeDict as _SafeDict

    # Write full traceback to a separate file so the agent isn't limited by prompt size
    traceback_path = orc_root / TRACEBACK_FILENAME
    orc_root.mkdir(parents=True, exist_ok=True)
    traceback_path.write_text(incident.traceback or "(no traceback)", encoding="utf-8")

    # ORC install path — agent can read orc_core/ files for ORC error analysis
    orc_install_path = str(Path(__file__).resolve().parent)

    template = load_role_template(ROLE_TEAMLEAD_TRIAGE)
    return template.format_map(_SafeDict(
        board_summary=format_board_summary(board),
        error_type=incident.error_type,
        source_slot_id=incident.source_slot_id,
        error_message=incident.error_message,
        error_traceback=incident.traceback[:2000],
        traceback_file=str(traceback_path),
        source_card_path=str(source_card.file_path) if source_card else "N/A",
        source_card_content=source_card.to_markdown() if source_card else "No card was being processed.",
        worktree_path=incident.worktree_path or "N/A (main workdir)",
        orc_install_path=orc_install_path,
        decision_path=decision_path,
    ))


# ── Decision parser ───────────────────────────────────────────────

@dataclass
class TriageDecision:
    classification: str   # "project" or "orc"
    target_role: str      # "coder", "architect", "reviewer", "integrator"
    fix_title: str
    body: str             # fix card body (project) or telegram message (orc)


def parse_incident_decision(decision_path: Path) -> TriageDecision:
    """Parse the AI agent's decision file.

    Raises ValueError if the file is missing required fields.
    """
    text = decision_path.read_text(encoding="utf-8")
    m = _FRONT_RE.match(text)
    if not m:
        raise ValueError(f"No YAML frontmatter in {decision_path}")

    raw_yaml, body = m.group(1), m.group(2).strip()
    data = yaml.safe_load(raw_yaml)
    if not isinstance(data, dict):
        raise ValueError(f"Frontmatter is not a dict in {decision_path}")

    classification = str(data.get("classification", "")).strip().lower()
    if classification not in ("project", "orc"):
        raise ValueError(f"Invalid classification: {classification!r} (expected 'project' or 'orc')")

    target_role = str(data.get("target_role", "coder")).strip().lower()
    fix_title = str(data.get("fix_title", "")).strip()

    if not fix_title:
        raise ValueError("Missing fix_title in decision frontmatter")

    return TriageDecision(
        classification=classification,
        target_role=target_role,
        fix_title=fix_title,
        body=body,
    )


def fallback_decision(incident: Incident) -> TriageDecision:
    """Generate a fallback decision when AI triage fails."""
    body = (
        f"# 1. Product Requirements\n\n"
        f"An error occurred while processing task {incident.source_task_id}.\n"
        f"Error type: {incident.error_type}\n"
        f"Error: {incident.error_message}\n\n"
        f"The fix must resolve this error so the task can proceed.\n\n"
        f"# 2. Technical Design & DoD\n\n"
        f"- [ ] Investigate the error traceback below\n"
        f"- [ ] Fix the root cause\n"
        f"- [ ] Verify the fix by running tests\n\n"
        f"Traceback:\n```\n{incident.traceback[:1500]}\n```\n\n"
        f"# 3. Implementation Notes\n\n\n"
        f"# 4. Feedback & Checklist\n"
    )
    return TriageDecision(
        classification="project",
        target_role="coder",
        fix_title=f"Fix error in {incident.source_task_id}: {incident.error_message[:80]}",
        body=body,
    )
