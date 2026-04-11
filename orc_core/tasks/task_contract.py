#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from typing import Optional

TASK_ID_RE = re.compile(
    r"^(?:\*\*)?(?P<id>[A-Z][A-Z0-9_-]+)(?::)?(?:\*\*)?(?:\s|$)",
    re.UNICODE,
)


def extract_task_id(text: str) -> Optional[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return None
    match = TASK_ID_RE.match(normalized)
    return match.group("id") if match else None
