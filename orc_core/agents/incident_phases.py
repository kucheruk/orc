#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Individual incident phase handlers — extracted from IncidentManager."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from ..board.kanban_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_REVIEW,
    Action,
)
from ..infra.io.logging import log_event
from ..models.task_types import Task
from ..use_cases.create_card import create_expedite_card
from ..tasks.task_execution_types import TaskExecutionStatus
from .teamlead_incident import (
    DECISION_FILENAME,
    FIX_CARD_PREFIX,
    INCIDENT_FIX_TIMEOUT,
    SCALE_DOWN_WAIT_TIMEOUT,
    Incident,
    IncidentPhase,
    build_incident_prompt,
    fallback_decision,
    parse_incident_decision,
)


def handle_scale_down(ctx, incident: Incident) -> Incident:
    """Scale down workers to 1, preparing for triage."""
    original_count, removed_ids = ctx.scale_down_workers(keep=1)
    intended_count = ctx.max_sessions - 1
    incident.original_worker_count = max(original_count, intended_count)
    incident.removed_session_ids = removed_ids
    ctx.publisher.log_incident(
        incident.id,
        f"Scaling down: {original_count} → 1 worker (removed {len(removed_ids)})",
    )
    log_event(ctx.log_path, "INFO", "incident scale_down",
              incident_id=incident.id, original=original_count, removed=len(removed_ids))
    if removed_ids:
        ctx.wait_slots_closed(removed_ids, timeout=SCALE_DOWN_WAIT_TIMEOUT)
    incident.phase = IncidentPhase.TRIAGE
    return incident


def handle_triage(ctx, slot, incident: Incident) -> Incident:
    """Run AI triage agent to classify the incident and decide on a fix."""
    sid = slot.session_id
    board = ctx.distributor.board
    source_card = board.card_by_id(incident.source_task_id) if incident.source_task_id else None

    orc_root = Path(ctx.workdir) / ".orc"
    orc_root.mkdir(parents=True, exist_ok=True)
    decision_path = orc_root / DECISION_FILENAME

    prompt = build_incident_prompt(incident, board, source_card, str(decision_path), orc_root)
    task = Task(task_id=f"triage-{incident.id}", text=f"[TL] Triage {incident.id}", done=False)
    slot.task = task

    ctx.publisher.log_incident(incident.id, "Running AI triage agent...")
    result = ctx.engine.execute(ctx.state_manager.make_request(task, prompt, ctx.workdir, sid, False, 600.0))

    try:
        if result and result.status == TaskExecutionStatus.COMPLETED and decision_path.exists():
            decision = parse_incident_decision(decision_path)
        else:
            ctx.publisher.log_incident(incident.id, "AI triage failed, using fallback")
            log_event(ctx.log_path, "WARN", "triage agent failed, using fallback",
                      incident_id=incident.id)
            decision = fallback_decision(incident)
    except Exception as exc:
        ctx.publisher.log_incident(incident.id, f"Decision parse failed: {exc}, using fallback")
        log_event(ctx.log_path, "WARN", "decision parse failed",
                  incident_id=incident.id, error=str(exc), error_type=type(exc).__name__)
        decision = fallback_decision(incident)
    finally:
        for cleanup_path in (decision_path, orc_root / "incident-traceback.txt"):
            if cleanup_path.exists():
                try:
                    cleanup_path.unlink()
                except OSError:
                    pass

    incident.error_class = decision.classification
    incident.target_role = decision.target_role
    incident.fix_title = decision.fix_title
    incident.fix_body = decision.body

    ctx.publisher.log_incident(
        incident.id,
        f"Triage result: {decision.classification}, role={decision.target_role}, "
        f"title={decision.fix_title[:80]}",
    )
    log_event(ctx.log_path, "INFO", "triage complete",
              incident_id=incident.id, classification=decision.classification,
              target_role=decision.target_role)

    if decision.classification == "orc":
        incident.phase = IncidentPhase.NOTIFY_HUMAN
    else:
        incident.phase = IncidentPhase.INJECT_FIX
    return incident


def handle_inject_fix(ctx, incident: Incident) -> Incident:
    """Create an expedite fix card on the board."""
    board = ctx.distributor.board
    base = incident.source_task_id or "unknown"
    fix_card_id = f"{FIX_CARD_PREFIX}{base}-{incident.id}"

    _ROLE_PLACEMENT: dict[str, tuple[str, str]] = {
        "coder":      (STAGE_CODING,   Action.CODING),
        "architect":  (STAGE_ESTIMATE, Action.ARCHITECT),
        "reviewer":   (STAGE_REVIEW,   Action.REVIEWING),
        "integrator": (STAGE_HANDOFF,  Action.INTEGRATING),
    }
    stage, action = _ROLE_PLACEMENT.get(incident.target_role, (STAGE_CODING, Action.CODING))

    create_expedite_card(
        board,
        incident.fix_title,
        incident.fix_body,
        card_id=fix_card_id,
        stage=stage,
        action=action,
        cos_justification=f"Incident {incident.id}: {incident.error_type}",
    )
    incident.fix_card_id = fix_card_id
    incident.fix_started_at = time.time()

    ctx.publisher.log_incident(
        incident.id,
        f"Fix card {fix_card_id} created in {stage} (role={incident.target_role})",
    )
    log_event(ctx.log_path, "INFO", "fix card injected",
              incident_id=incident.id, fix_card_id=fix_card_id,
              stage=stage, target_role=incident.target_role)

    incident.phase = IncidentPhase.WAIT_FOR_FIX
    return incident


def handle_wait_for_fix(ctx, incident: Incident) -> Optional[Incident]:
    """Poll for fix card completion, escalate on timeout or failure."""
    board = ctx.distributor.board
    fix_card = board.card_by_id(incident.fix_card_id)

    if fix_card and fix_card.stage == STAGE_DONE:
        ctx.publisher.log_incident(incident.id, f"Fix {incident.fix_card_id} completed!")
        log_event(ctx.log_path, "INFO", "fix completed",
                  incident_id=incident.id, fix_card_id=incident.fix_card_id)
        incident.phase = IncidentPhase.SCALE_UP
        return incident

    if incident.fix_card_id in ctx.failed_tasks:
        ctx.publisher.log_incident(
            incident.id,
            f"Fix card {incident.fix_card_id} itself failed — escalating to human",
        )
        ctx.block_fix_card(incident)
        ctx.send_incident_telegram(
            incident,
            f"Fix card {incident.fix_card_id} failed while trying to resolve "
            f"incident {incident.id}.\n"
            f"Original error: {incident.error_message[:500]}",
        )
        ctx.scale_up_workers(incident.original_worker_count)
        return None

    elapsed = time.time() - incident.fix_started_at
    if elapsed > INCIDENT_FIX_TIMEOUT:
        ctx.publisher.log_incident(
            incident.id,
            f"Fix timeout ({INCIDENT_FIX_TIMEOUT:.0f}s) — escalating to human",
        )
        ctx.block_fix_card(incident)
        ctx.send_incident_telegram(
            incident,
            f"Fix card {incident.fix_card_id} timed out after {elapsed:.0f}s.\n"
            f"Incident {incident.id}: {incident.error_message[:500]}",
        )
        ctx.scale_up_workers(incident.original_worker_count)
        return None

    return incident  # Keep waiting


def handle_scale_up(ctx, incident: Incident) -> None:
    """Restore worker count after successful fix."""
    new_ids = ctx.scale_up_workers(incident.original_worker_count)
    ctx.publisher.log_incident(
        incident.id,
        f"Scaling up: restored to {incident.original_worker_count} workers "
        f"(added {len(new_ids)})",
    )
    log_event(ctx.log_path, "INFO", "incident scale_up",
              incident_id=incident.id, target=incident.original_worker_count,
              added=len(new_ids))
    return None


def handle_notify_human(ctx, incident: Incident) -> None:
    """Escalate to human via Telegram for ORC-level bugs."""
    ctx.publisher.log_incident(incident.id, "ORC error — notifying human via Telegram")

    message = incident.fix_body or (
        f"ORC BUG in incident {incident.id}\n"
        f"Error: {incident.error_message}\n"
        f"Traceback:\n{incident.traceback[:1500]}"
    )
    ctx.send_incident_telegram(incident, message)

    if incident.source_task_id:
        board = ctx.distributor.board
        card = board.card_by_id(incident.source_task_id)
        if card and card.action != Action.BLOCKED:
            card.block()
            board.save_card(card)
            ctx.distributor.release_card(card.id)

    log_event(ctx.log_path, "WARN", "orc error notified, workers remain scaled down",
              incident_id=incident.id, source_task=incident.source_task_id)
    return None
