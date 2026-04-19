#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constructs and persists new KanbanCards — extracted from KanbanBoard."""

from __future__ import annotations

from pathlib import Path

from .action_constants import Action
from .clock import Clock, SystemClock
from .card_repository import CardRepository
from .card_sections import new_card_body
from .kanban_card import KanbanCard
from .kanban_card_serializer import card_to_markdown
from .stage_constants import STAGE_CODING, STAGE_INBOX


class KanbanCardFactory:
    """Creates new cards and writes them to the repository.

    The factory knows how to build card dataclasses with proper defaults
    (timestamps, bodies, scores) and persist them. It does NOT touch the
    board's in-memory list — the caller should register the returned card
    via ``KanbanBoard.register_card``.
    """

    def __init__(
        self,
        tasks_dir: Path,
        *,
        repo: CardRepository,
        clock: Clock | None = None,
    ) -> None:
        self._tasks_dir = tasks_dir
        self._repo = repo
        self._clock: Clock = clock or SystemClock()

    def create_inbox(self, card_id: str, title: str) -> KanbanCard:
        card = KanbanCard(
            id=card_id, title=title, stage=STAGE_INBOX, action=Action.PRODUCT,
            created_at=self._clock.now_iso(),
            body=new_card_body(),
        )
        return self._persist(card, STAGE_INBOX)

    def create_expedite(
        self,
        card_id: str,
        title: str,
        body: str,
        *,
        stage: str = STAGE_CODING,
        action: str = Action.CODING,
        cos_justification: str = "",
    ) -> KanbanCard:
        """Create an expedite card directly at the given stage, bypassing inbox."""
        card = KanbanCard(
            id=card_id, title=title, stage=stage, action=action,
            class_of_service="expedite",
            cos_justification=cos_justification,
            value_score=100, effort_score=20,
            created_at=self._clock.now_iso(),
            body=body,
        )
        return self._persist(card, stage)

    def _persist(self, card: KanbanCard, stage: str) -> KanbanCard:
        stage_dir = self._tasks_dir / stage
        self._repo.ensure_dir(stage_dir)
        path = stage_dir / f"{card.id}.md"
        card.touch()
        card.advance_state_version()
        self._repo.write_card_text(path, card_to_markdown(card))
        card.file_path = path
        return card
