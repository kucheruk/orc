#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .backend import Backend


class AgentNotInstalledError(RuntimeError):
    pass


def ensure_agent_installed(backend: Optional["Backend"] = None) -> None:
    if backend is None:
        from .backend import get_backend
        backend = get_backend()
    backend.ensure_installed()
