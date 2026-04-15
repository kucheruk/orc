#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: process the result of an agent task execution.

Decides whether execution succeeded, validates agent output against
card constraints, records outcomes, and handles failures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Protocol

from ...board.kanban_board import KanbanBoard
from ...board.kanban_card import KanbanCard
from ...log import log_event

# Callable type for processing agent output: (board, card, role) -> list[errors]
AgentResultProcessor = Callable[[KanbanBoard, KanbanCard, str], list[str]]
from ...tasks.execution.request import TaskExecutionResult
from ...models.task_status import TaskExecutionStatus


class OutcomeTracker(Protocol):
    """Port for tracking task outcomes (fail/success counts)."""
    def record_completed(self, card_id: str) -> None: ...
    def record_failed(self, card_id: str) -> None: ...
    def increment_fail_count(self, card_id: str) -> int: ...
    def reset_fail_count(self, card_id: str) -> None: ...


class CompletionPublisher(Protocol):
    """Port for publishing task lifecycle events."""
    def log_complete(self, card_id: str, role: str, elapsed: float) -> None: ...
    def _emit(self, kind: str, card_id: str, message: str) -> None: ...


class CompletionNotifier(Protocol):
    """Port for sending completion notifications."""
    def notify_completion(
        self, card: KanbanCard, role: str,
        old_stage: str, old_action: str, old_cos: str, elapsed: float,
    ) -> None: ...
    def send_telegram(self, text: str) -> None: ...


def process_completed_task(
    board: KanbanBoard,
    card: KanbanCard,
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
    else:
        publisher._emit("escalate", card.id,
                        f"{card.id} validation failed: {'; '.join(errors[:3])}")
        log_event(log_path, "WARN", "agent output validation failed",
                  task_id=card.id, role=role, errors=str(errors))
        outcomes.record_failed(card.id)
    return errors


def handle_task_failure(
    card: KanbanCard,
    reason: str,
    outcomes: OutcomeTracker,
    publisher: CompletionPublisher,
    role: str,
) -> None:
    """Record a failed task execution and publish escalation."""
    publisher._emit("escalate", card.id, f"{card.id} {role} failed: {reason}")
    outcomes.record_failed(card.id)


FAIL_BLOCK_THRESHOLD = 3


def escalate_if_threshold_reached(
    card: KanbanCard,
    error_desc: str,
    board: KanbanBoard,
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
        card.block(error_desc)
        board.save_card(card)
        publisher._emit("escalate", card.id,
                        f"{card.id} marked Blocked after {count} consecutive failures: {error_desc}")
        log_event(log_path, "WARN", "card blocked after repeated failures",
                  task_id=card.id, fail_count=count, error=error_desc)
        notifier.send_telegram(
            f"\U0001f6ab {card.id} заблокирована после {count} подряд ошибок: {error_desc}",
        )
    except (OSError, ConnectionError, TimeoutError, ValueError):
        pass
    return True
