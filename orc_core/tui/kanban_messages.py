#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban-specific TUI messages for board updates, journal, and inbox."""

from textual.message import Message

from ..board.kanban_snapshot import JournalEntry, KanbanBoardSnapshot


class BoardUpdated(Message):
    def __init__(self, snapshot: KanbanBoardSnapshot) -> None:
        self.snapshot = snapshot
        super().__init__()


class JournalEntryAdded(Message):
    def __init__(self, entry: JournalEntry) -> None:
        self.entry = entry
        super().__init__()


class InboxCardRequested(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class UnblockCardRequested(Message):
    def __init__(self, card_id: str, directive: str) -> None:
        self.card_id = card_id
        self.directive = directive
        super().__init__()


class TeamleadDirectiveRequested(Message):
    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()
