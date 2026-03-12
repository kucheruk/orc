#!/usr/bin/env python3
# -*- coding: utf-8 -*-

MAIN_INTEGRATION_PREFLIGHT_FAILED = "main_integration_preflight_failed"


def _sanitize_reason_part(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _extract_main_integration_detail(error: str) -> str:
    normalized = _sanitize_reason_part(error)
    if not normalized:
        return ""
    prefix = "base repository is dirty before integration:"
    lowered = normalized.lower()
    if lowered.startswith(prefix):
        return normalized[len(prefix) :].strip()
    if ":" in normalized:
        return normalized.split(":", 1)[1].strip()
    return normalized


def build_main_integration_preflight_reason(failure_kind: str, error: str) -> str:
    parts = [MAIN_INTEGRATION_PREFLIGHT_FAILED, _sanitize_reason_part(failure_kind) or "unknown"]
    detail = _extract_main_integration_detail(error)
    if detail:
        parts.append(detail)
    return ":".join(parts)


def format_known_failure_message(reason: str) -> str | None:
    normalized = _sanitize_reason_part(reason)
    if not normalized.startswith(f"{MAIN_INTEGRATION_PREFLIGHT_FAILED}:"):
        return None
    _, _, remainder = normalized.partition(":")
    failure_kind, _, detail = remainder.partition(":")
    if failure_kind == "dirty_base_repo":
        details_suffix = f" Проблемные пути: {detail}." if detail else ""
        return (
            "Базовый git-репозиторий грязный перед интеграцией в main/master."
            f"{details_suffix} ORC остановился, чтобы не смешать локальные изменения"
            " с переносом task commit. Проверьте `git status --porcelain` и либо"
            " закоммитьте, либо уберите эти изменения, затем повторите запуск."
        )
    if failure_kind == "main_branch_missing":
        return (
            "ORC не нашёл целевую ветку для main integration."
            f" Деталь: {detail or 'unknown'}."
        )
    if failure_kind == "git_status_failed":
        return (
            "ORC не смог прочитать состояние git-репозитория перед интеграцией."
            f" Деталь: {detail or 'unknown'}."
        )
    return None
