#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write single-card mutations back to the filesystem via CardRepository."""

from __future__ import annotations

import logging
import threading

from ..text_parse import parse_frontmatter
from .board_listeners import BoardListenerBus
from .card_repository import CardRepository
from .kanban_card import KanbanCard
from .kanban_card_serializer import card_to_markdown

_logger = logging.getLogger(__name__)


def _peek_state_version(card: KanbanCard) -> int | None:
    """Read the state_version currently on disk for this card, or None if the
    file is missing / unreadable / has no frontmatter."""
    path = card.file_path
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        data, _ = parse_frontmatter(text, str(path))
    except ValueError:
        return None
    raw = data.get("state_version")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _has_external_edit(card: KanbanCard) -> bool:
    """True when the card file on disk has a newer state_version than the
    in-memory copy — a signal that something outside ORC (an operator
    hand-editing the .md, a parallel process) wrote to the file since this
    card was last loaded. Writing over that change would silently clobber
    it; the caller must refresh from disk instead.
    """
    disk = _peek_state_version(card)
    if disk is None:
        return False
    return disk > int(card.state_version or 0)


class BoardCardPersistence:
    """Apply and persist mutations to a single card (save, assign, release).

    Every mutation checks the on-disk state_version against the in-memory
    copy before writing. If disk is newer, the save is aborted and the
    next board.refresh() will pick up the external change — this prevents
    ORC from overwriting manual operator edits or writes from a parallel
    process. A stale-memory save would otherwise "win" the race: we'd
    push our older YAML over the newer on-disk YAML and the operator's
    hand-edit would vanish.
    """

    def __init__(
        self,
        *,
        repo: CardRepository,
        lock: threading.RLock,
        listeners: BoardListenerBus,
    ) -> None:
        self._repo = repo
        self._lock = lock
        self._listeners = listeners

    def _abort_if_externally_edited(self, card: KanbanCard, op: str) -> bool:
        if _has_external_edit(card):
            _logger.warning(
                "board_card_persistence: aborting %s for %s — disk state_version "
                "is newer than memory, treating as external edit (operator / "
                "parallel writer). Board.refresh() will reconcile on the next "
                "tick; the in-flight mutation is dropped to avoid clobber.",
                op, card.id,
            )
            return True
        return False

    def save(self, card: KanbanCard, *, old_action: str = "", role: str = "") -> None:
        with self._lock:
            if self._abort_if_externally_edited(card, "save"):
                return
            card.touch()  # touch() includes refresh_roi()
            card.advance_state_version()
            if card.file_path:
                self._repo.write_card_text(card.file_path, card_to_markdown(card))
        if old_action and old_action != card.action:
            self._listeners.fire_action_change(card.id, old_action, card.action, role)

    def assign(self, card: KanbanCard, agent_id: str) -> None:
        with self._lock:
            if self._abort_if_externally_edited(card, "assign"):
                return
            card.assign(agent_id)
            card.advance_state_version()
            if card.file_path:
                self._repo.write_card_text(card.file_path, card_to_markdown(card))

    def release(self, card: KanbanCard) -> None:
        with self._lock:
            if self._abort_if_externally_edited(card, "release"):
                return
            card.release()
            card.advance_state_version()
            if card.file_path:
                self._repo.write_card_text(card.file_path, card_to_markdown(card))
