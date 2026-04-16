#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild in-memory board state from the tasks/ folder tree via CardRepository."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .card_repository import CardRepository
from .kanban_card import KanbanCard, parse_card
from .stage_constants import STAGES
from .wip_manager import WIPManager

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HydrationResult:
    cards: list[KanbanCard]
    parse_errors: list[tuple[str, str]]
    stage_mtimes: dict[str, float]


class BoardHydration:
    """Read cards and WIP limits from disk; pure producer of state snapshots."""

    def __init__(self, tasks_dir: Path, repo: CardRepository) -> None:
        self._tasks_dir = tasks_dir
        self._repo = repo

    def is_fresh(self, last_mtimes: dict[str, float]) -> bool:
        if not last_mtimes:
            return False
        return self._repo.scan_stage_mtimes(self._tasks_dir) == last_mtimes

    def rebuild(self, wip: WIPManager) -> HydrationResult:
        cards: list[KanbanCard] = []
        errors: list[tuple[str, str]] = []
        wip.reset()
        for stage in STAGES:
            stage_dir = self._tasks_dir / stage
            if not stage_dir.is_dir():
                continue
            self._read_index(stage_dir, stage, wip)
            self._read_cards(stage_dir, stage, cards, errors)
        cards = self._dedup_cards(cards)
        for card in cards:
            card.refresh_roi()
        mtimes = self._repo.scan_stage_mtimes(self._tasks_dir)
        return HydrationResult(cards, errors, mtimes)

    def _read_index(self, stage_dir: Path, stage: str, wip: WIPManager) -> None:
        try:
            data = self._repo.read_index_data(stage_dir)
            if data:
                wip.set_limit_from_index(stage, data.get("wip_limit"))
        except Exception as exc:
            _logger.warning("Failed to read index in %s: %s", stage_dir, exc)

    def _dedup_cards(self, cards: list[KanbanCard]) -> list[KanbanCard]:
        """When the same card_id exists in multiple stages, keep the newest copy and delete the stale file."""
        stage_order = {s: i for i, s in enumerate(STAGES)}
        seen: dict[str, KanbanCard] = {}
        for card in cards:
            prev = seen.get(card.id)
            if prev is None:
                seen[card.id] = card
                continue
            card_key = (card.updated_at, stage_order.get(card.stage, 0))
            prev_key = (prev.updated_at, stage_order.get(prev.stage, 0))
            keep, drop = (card, prev) if card_key >= prev_key else (prev, card)
            _logger.warning("Duplicate card %s in %s and %s — keeping %s, removing %s",
                            card.id, card.stage, prev.stage, keep.stage, drop.stage)
            if drop.file_path and drop.file_path.exists():
                drop.file_path.unlink()
            seen[card.id] = keep
        return list(seen.values())

    def _read_cards(self, stage_dir: Path, stage: str,
                    cards: list[KanbanCard], errors: list[tuple[str, str]]) -> None:
        for md in self._repo.list_card_files(stage_dir):
            try:
                text = self._repo.read_card_text(md)
                card = parse_card(text, file_path=md)
                card.stage = stage  # trust folder over frontmatter
                cards.append(card)
            except Exception as exc:
                _logger.error("CARD LOST — failed to parse %s: %s", md, exc, exc_info=True)
                errors.append((str(md), str(exc)))
