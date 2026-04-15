#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Backend(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def cli_binary(self) -> str: ...

    def ensure_installed(self) -> None: ...

    def build_agent_cmd(
        self,
        *,
        model: str,
        prompt: str | None = None,
        resume_id: str | None = None,
        resume_latest: bool = False,
        resume_prompt: str | None = None,
    ) -> list[str]: ...

    def setup_hooks(self, workdir: str, log_path: Path) -> None: ...

    def get_resume_id(self, workdir: str, log_path: Path) -> str | None: ...

    def default_model(self) -> str: ...

    def list_models_cmd(self) -> list[str] | None: ...


_BACKEND_REGISTRY: dict[str, tuple[str, str]] = {
    "cursor": ("orc_core.backends.cursor", "CursorBackend"),
    "claude": ("orc_core.backends.claude", "ClaudeBackend"),
    "codex": ("orc_core.backends.codex", "CodexBackend"),
}

SUPPORTED_BACKENDS: tuple[str, ...] = tuple(_BACKEND_REGISTRY)


def register_backend(name: str, module_path: str, class_name: str) -> None:
    """Register a new backend. Updates SUPPORTED_BACKENDS."""
    global SUPPORTED_BACKENDS
    _BACKEND_REGISTRY[name] = (module_path, class_name)
    SUPPORTED_BACKENDS = tuple(sorted(_BACKEND_REGISTRY))


def get_backend(name: str = "cursor") -> Backend:
    entry = _BACKEND_REGISTRY.get(name)
    if entry is None:
        raise ValueError(f"Unknown backend: {name!r}. Supported: {', '.join(sorted(_BACKEND_REGISTRY))}")
    module_path, class_name = entry
    mod = __import__(module_path, fromlist=[class_name])
    return getattr(mod, class_name)()
