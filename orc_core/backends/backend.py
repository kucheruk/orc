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


class BackendRegistry:
    """Instance-scoped registry of backend implementations."""

    def __init__(self, entries: dict[str, tuple[str, str]] | None = None) -> None:
        self._entries: dict[str, tuple[str, str]] = dict(entries or {})

    def register(self, name: str, module_path: str, class_name: str) -> None:
        self._entries[name] = (module_path, class_name)

    def get(self, name: str = "cursor") -> Backend:
        entry = self._entries.get(name)
        if entry is None:
            raise ValueError(
                f"Unknown backend: {name!r}. Supported: {', '.join(sorted(self._entries))}"
            )
        module_path, class_name = entry
        mod = __import__(module_path, fromlist=[class_name])
        return getattr(mod, class_name)()

    @property
    def supported(self) -> tuple[str, ...]:
        return tuple(self._entries)


DEFAULT_BACKEND_REGISTRY = BackendRegistry(
    {
        "cursor": ("orc_core.backends.cursor", "CursorBackend"),
        "claude": ("orc_core.backends.claude", "ClaudeBackend"),
        "codex": ("orc_core.backends.codex", "CodexBackend"),
    }
)


def register_backend(name: str, module_path: str, class_name: str) -> None:
    DEFAULT_BACKEND_REGISTRY.register(name, module_path, class_name)


def get_backend(name: str = "cursor") -> Backend:
    return DEFAULT_BACKEND_REGISTRY.get(name)


def __getattr__(attr: str):
    if attr == "SUPPORTED_BACKENDS":
        return DEFAULT_BACKEND_REGISTRY.supported
    raise AttributeError(f"module 'orc_core.backends.backend' has no attribute {attr!r}")
