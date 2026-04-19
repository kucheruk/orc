#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: process the result of an agent task execution.

Decides whether execution succeeded, validates agent output against
card constraints, records outcomes, and handles failures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Protocol

from ...board.gateway import BoardGateway, CardView
from ...board.use_cases.escalate_card import escalate_card
from ...log import log_event

# Callable type for processing agent output: (board, card, role) -> list[errors]
AgentResultProcessor = Callable[[BoardGateway, CardView, str], list[str]]
from ..execution.request import TaskExecutionResult
from ..status import TaskExecutionStatus


class OutcomeTracker(Protocol):
    """Port for tracking task outcomes (fail/success counts)."""
    def record_completed(self, card_id: str) -> None: ...
    def record_failed(self, card_id: str) -> None: ...
    def increment_fail_count(self, card_id: str) -> int: ...
    def reset_fail_count(self, card_id: str) -> None: ...


class CompletionPublisher(Protocol):
    """Port for publishing task lifecycle events."""
    def log_complete(self, card_id: str, role: str, elapsed: float) -> None: ...
    def emit(self, kind: str, card_id: str, message: str) -> None: ...


class CompletionNotifier(Protocol):
    """Port for emitting task-lifecycle notifications."""
    def notify_completion(
        self, card: CardView, role: str,
        old_stage: str, old_action: str, old_cos: str, elapsed: float,
    ) -> None: ...
    def notify_card_blocked(self, card_id: str, count: int, reason: str) -> None: ...


def process_completed_task(
    board: BoardGateway,
    card: CardView,
    role: str,
    elapsed: float,
    outcomes: OutcomeTracker,
    publisher: CompletionPublisher,
    notifier: CompletionNotifier,
    log_path: Path,
    agent_result_processor: AgentResultProcessor,
) -> list[str]:
    """Process a successfully completed task execution.

    Validates agent output, records outcome, sends notifications.
    Returns list of validation errors (empty on success).
    """
    old_stage = card.stage
    old_action = card.action
    old_cos = card.class_of_service
    errors = agent_result_processor(board, card, role)
    if not errors:
        outcomes.record_completed(card.id)
        publisher.log_complete(card.id, role, elapsed)
        notifier.notify_completion(card, role, old_stage, old_action, old_cos, elapsed)
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.ATTEMPT_FINISH,
            "applied",
            task_id=card.id,
            context={"role": role, "stage": card.stage, "elapsed_s": int(elapsed)},
        )
        if old_stage != card.stage:
            emit_signal(
                SignalKind.CARD_MOVED,
                "pipeline_transition",
                task_id=card.id,
                context={"from": old_stage, "to": card.stage, "role": role,
                         "action_from": old_action, "action_to": card.action},
            )
        from ...board.stage_constants import STAGE_DONE
        if card.stage == STAGE_DONE and old_stage != STAGE_DONE:
            emit_signal(
                SignalKind.CARD_DONE,
                "integration_complete" if role == "integrator" else "pipeline_complete",
                task_id=card.id,
                context={"role": role, "elapsed_s": int(elapsed)},
            )
    else:
        publisher.emit("escalate", card.id,
                        f"{card.id} validation failed: {'; '.join(errors[:3])}")
        log_event(log_path, "WARN", "agent output validation failed",
                  task_id=card.id, role=role, errors=str(errors))
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.ATTEMPT_VALIDATION_FAILED,
            "; ".join(errors[:3])[:200],
            task_id=card.id,
            context={"role": role, "stage": card.stage, "errors": errors[:5]},
        )
        outcomes.record_failed(card.id)
    return errors


def handle_task_failure(
    card: CardView,
    reason: str,
    outcomes: OutcomeTracker,
    publisher: CompletionPublisher,
    role: str,
) -> None:
    """Record a failed task execution and publish escalation."""
    publisher.emit("escalate", card.id, f"{card.id} {role} failed: {reason}")
    outcomes.record_failed(card.id)


FAIL_BLOCK_THRESHOLD = 3


def escalate_if_threshold_reached(
    card: CardView,
    error_desc: str,
    board: BoardGateway,
    outcomes: OutcomeTracker,
    publisher: CompletionPublisher,
    notifier: CompletionNotifier,
    log_path: Path,
) -> bool:
    """Increment failure count; block card if threshold reached. Returns True if blocked."""
    count = outcomes.increment_fail_count(card.id)
    if count < FAIL_BLOCK_THRESHOLD:
        return False
    try:
        escalate_card(board, card, reason=error_desc)
        publisher.emit("escalate", card.id,
                        f"{card.id} marked Blocked after {count} consecutive failures: {error_desc}")
        log_event(log_path, "WARN", "card blocked after repeated failures",
                  task_id=card.id, fail_count=count, error=error_desc)
        notifier.notify_card_blocked(card.id, count, error_desc)
        from ...signals import SignalKind, emit_signal
        emit_signal(
            SignalKind.CARD_BLOCKED,
            "failure_threshold_reached",
            task_id=card.id,
            context={"fail_count": count, "error": str(error_desc)[:300]},
        )
    except (OSError, ConnectionError, TimeoutError, ValueError) as exc:
        log_event(log_path, "ERROR", "failed to block card after repeated failures",
                  task_id=card.id, fail_count=count, error=str(exc))
    return True
