#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from orc_core.tasks.completion.checks import (
    CheckRegistry,
    DEFAULT_CHECK_REGISTRY,
    check_backlog_done_idle,
    check_escape,
    check_followup_prompt,
    check_pid_missing,
    check_process_exited,
    check_stall,
    check_task_file_removed,
    check_tokens_stuck,
    check_ttl,
    maybe_report,
)


EXPECTED_ORDER = (
    ("check_escape", check_escape),
    ("check_task_file_removed", check_task_file_removed),
    ("check_pid_missing", check_pid_missing),
    ("check_backlog_done_idle", check_backlog_done_idle),
    ("maybe_report", maybe_report),
    ("check_tokens_stuck", check_tokens_stuck),
    ("check_process_exited", check_process_exited),
    ("check_followup_prompt", check_followup_prompt),
    ("check_stall", check_stall),
    ("check_ttl", check_ttl),
)


def test_default_registry_contains_all_ten_checks() -> None:
    entries = list(DEFAULT_CHECK_REGISTRY.iter_ordered())
    assert len(entries) == 10
    registered_fns = {fn for _name, fn in entries}
    expected_fns = {fn for _name, fn in EXPECTED_ORDER}
    assert registered_fns == expected_fns


def test_default_registry_order_matches_legacy_chain() -> None:
    entries = list(DEFAULT_CHECK_REGISTRY.iter_ordered())
    assert entries == list(EXPECTED_ORDER)


def test_register_raises_on_priority_conflict() -> None:
    registry = CheckRegistry()
    registry.register("first", 10, check_escape)
    with pytest.raises(ValueError) as exc_info:
        registry.register("second", 10, check_ttl)
    message = str(exc_info.value)
    assert "second" in message
    assert "10" in message
    assert "first" in message


def test_iter_ordered_sorts_by_priority_ascending() -> None:
    registry = CheckRegistry()
    registry.register("late", 100, check_ttl)
    registry.register("early", 5, check_escape)
    registry.register("mid", 50, maybe_report)
    entries = list(registry.iter_ordered())
    assert [name for name, _fn in entries] == ["early", "mid", "late"]
