#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task execution status enums — the most-imported types from the task layer."""

from enum import StrEnum


class TaskExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CONTINUE = "continue"


class TaskCompletionStatus(StrEnum):
    COMPLETED = "completed"
    STALLED = "stalled"
    TTL_EXCEEDED = "ttl_exceeded"
    PROCESS_EXITED = "process_exited"
    WAITING_FOR_INPUT = "waiting_for_input"
    MODEL_UNAVAILABLE = "model_unavailable"


RESTART_REASON_TEXT = {
    TaskCompletionStatus.STALLED: "Ты перестал выдавать результат (завис). Переоцени свой подход.",
    TaskCompletionStatus.TTL_EXCEEDED: "Ты превысил лимит времени. Сделай коммит текущего прогресса или выбери более простой путь.",
    TaskCompletionStatus.PROCESS_EXITED: "Твой процесс неожиданно завершился (возможно, ошибка синтаксиса в bash).",
}
