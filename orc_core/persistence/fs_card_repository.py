#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filesystem-backed card repository — implements CardRepository port."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Optional

import yaml

from ..board.limits_constants import INDEX_FILENAME
from ..board.stage_constants import STAGES
from ..board.kanban_card import KanbanCard, parse_card
from ..infra.io.atomic_io import write_text_atomic


class FsCardRepository:
    """Filesystem-backed card repository."""

    def read_card_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")

    def write_card_text(self, path: Path, text: str) -> None:
        write_text_atomic(path, text)

    def move_card_file(self, old_path: Path, new_dir: Path) -> Path:
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / old_path.name
        shutil.move(str(old_path), str(new_path))
        return new_path

    def list_card_files(self, stage_dir: Path) -> list[Path]:
        return sorted(
            md for md in stage_dir.glob("*.md")
            if md.name != INDEX_FILENAME
        )

    def read_index_data(self, stage_dir: Path) -> Optional[dict[str, Any]]:
        idx = stage_dir / INDEX_FILENAME
        if not idx.exists():
            return None
        text = idx.read_text(encoding="utf-8")
        m = re.match(r"\A---\n(.*?\n)---", text, re.DOTALL)
        if not m:
            return None
        return yaml.safe_load(m.group(1)) or {}

    def write_index(self, stage_dir: Path, data: str) -> None:
        self.ensure_dir(stage_dir)
        idx = stage_dir / INDEX_FILENAME
        idx.write_text(data, encoding="utf-8")

    def ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def scan_stage_mtimes(self, tasks_dir: Path) -> dict[str, float]:
        result: dict[str, float] = {}
        for stage in STAGES:
            stage_dir = tasks_dir / stage
            if stage_dir.is_dir():
                try:
                    result[stage] = stage_dir.stat().st_mtime
                except OSError:
                    pass
        return result

    def read_card(self, path: Path) -> KanbanCard:
        text = self.read_card_text(path)
        return parse_card(text, file_path=path)

    def write_card(self, card: KanbanCard, path: Path | None = None) -> None:
        target = path or card.file_path
        if target is None:
            raise ValueError("No path specified for card write")
        self.write_card_text(target, card.to_markdown())
        card.file_path = target
