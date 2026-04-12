#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Card persistence port — domain interface for card storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .kanban_card import KanbanCard


class CardRepository(Protocol):
    """Port for card persistence — domain logic depends on this, not on FS directly."""

    def read_card_text(self, path: Path) -> str: ...

    def write_card_text(self, path: Path, text: str) -> None: ...

    def move_card_file(self, old_path: Path, new_dir: Path) -> Path: ...

    def list_card_files(self, stage_dir: Path) -> list[Path]: ...

    def read_index_data(self, stage_dir: Path) -> Optional[dict[str, Any]]: ...

    def write_index(self, stage_dir: Path, data: str) -> None: ...

    def ensure_dir(self, path: Path) -> None: ...

    def scan_stage_mtimes(self, tasks_dir: Path) -> dict[str, float]: ...

    def read_card(self, path: Path) -> "KanbanCard": ...

    def write_card(self, card: "KanbanCard", path: Path | None = None) -> None: ...
