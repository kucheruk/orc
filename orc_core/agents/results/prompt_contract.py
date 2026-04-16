#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared prompt fragments for structured agent result output."""

from __future__ import annotations

from typing import Iterable


def build_result_contract_block(
    *,
    result_file: str,
    run_id: str,
    payload_kind: str,
    required_payload_keys: Iterable[str],
) -> str:
    payload_keys = "\n".join(f"- {key}" for key in required_payload_keys)
    return (
        "## Structured Result\n"
        "Do not use markdown files as a control-plane output.\n"
        f"Write the final JSON result to `{result_file}`.\n"
        f"Set `run_id` to `{run_id}`.\n"
        f"Set `payload_kind` to `{payload_kind}`.\n\n"
        "Required top-level keys:\n"
        "- schema_version\n"
        "- payload_kind\n"
        "- role\n"
        "- run_id\n"
        "- summary\n"
        "- payload\n\n"
        "Required payload keys:\n"
        f"{payload_keys}\n"
    )
