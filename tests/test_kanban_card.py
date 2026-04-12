#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.board.kanban_card import (
    KanbanCard,
    new_card_body,
    parse_card,
    validate_card,
)
from orc_core.infra.adapters.fs_card_repository import FsCardRepository

_repo = FsCardRepository()
read_card = _repo.read_card
write_card = _repo.write_card


SAMPLE_CARD = """\
---
id: TASK-001
title: Add login page
stage: 4_Coding
action: Coding
class_of_service: standard
cos_justification: ''
deadline: ''
value_score: 80
effort_score: 30
roi: 2.67
dependencies:
  - TASK-000
loop_count: 1
assigned_agent: s2
created_at: '2026-03-28T12:00:00+00:00'
updated_at: '2026-03-28T13:00:00+00:00'
---

# 1. Product Requirements

Login page with OAuth2.

# 2. Technical Design & DoD

Use Keycloak OIDC.
"""


class TestParseCard(unittest.TestCase):

    def test_parse_basic(self):
        card = parse_card(SAMPLE_CARD)
        self.assertEqual(card.id, "TASK-001")
        self.assertEqual(card.title, "Add login page")
        self.assertEqual(card.stage, "4_Coding")
        self.assertEqual(card.action, "Coding")
        self.assertEqual(card.class_of_service, "standard")
        self.assertEqual(card.value_score, 80)
        self.assertEqual(card.effort_score, 30)
        self.assertAlmostEqual(card.roi, 2.67)
        self.assertEqual(card.dependencies, ["TASK-000"])
        self.assertEqual(card.loop_count, 1)
        self.assertEqual(card.assigned_agent, "s2")
        self.assertIn("Login page with OAuth2", card.body)

    def test_parse_no_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            parse_card("No frontmatter here")

    def test_parse_empty_frontmatter(self):
        card = parse_card("---\nid: ''\n---\nBody text")
        self.assertEqual(card.id, "")
        self.assertEqual(card.body, "Body text")

    def test_parse_dependencies_single(self):
        text = "---\nid: X\ndependencies: TASK-1\n---\n"
        card = parse_card(text)
        self.assertEqual(card.dependencies, ["TASK-1"])

    def test_parse_dependencies_none(self):
        text = "---\nid: X\ndependencies:\n---\n"
        card = parse_card(text)
        self.assertEqual(card.dependencies, [])


class TestComputeROI(unittest.TestCase):

    def test_basic(self):
        card = KanbanCard(id="T", value_score=90, effort_score=30)
        self.assertAlmostEqual(card.compute_roi(), 3.0)

    def test_zero_effort(self):
        card = KanbanCard(id="T", value_score=90, effort_score=0)
        self.assertAlmostEqual(card.compute_roi(), 0.0)

    def test_refresh_roi(self):
        card = KanbanCard(id="T", value_score=50, effort_score=25)
        card.refresh_roi()
        self.assertAlmostEqual(card.roi, 2.0)


class TestRoundTrip(unittest.TestCase):

    def test_serialize_and_parse(self):
        card = KanbanCard(
            id="RT-01",
            title="Roundtrip test",
            stage="3_Todo",
            action="Coding",
            class_of_service="expedite",
            cos_justification="Server down, losing $500/hr",
            value_score=95,
            effort_score=10,
            dependencies=["RT-00"],
            body=new_card_body(),
        )
        card.refresh_roi()
        md = card.to_markdown()
        parsed = parse_card(md)
        self.assertEqual(parsed.id, "RT-01")
        self.assertEqual(parsed.class_of_service, "expedite")
        self.assertEqual(parsed.cos_justification, "Server down, losing $500/hr")
        self.assertAlmostEqual(parsed.roi, 9.5)
        self.assertEqual(parsed.dependencies, ["RT-00"])

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "TASK-W.md"
            card = KanbanCard(id="TASK-W", title="Write test", body="Hello")
            write_card(card, path)
            loaded = read_card(path)
            self.assertEqual(loaded.id, "TASK-W")
            self.assertEqual(loaded.body, "Hello")


class TestValidation(unittest.TestCase):

    def test_valid_card(self):
        card = KanbanCard(id="V-1", value_score=50, effort_score=50)
        self.assertEqual(validate_card(card), [])

    def test_missing_id(self):
        card = KanbanCard(id="")
        errors = validate_card(card)
        self.assertTrue(any("id" in e for e in errors))

    def test_expedite_needs_justification(self):
        card = KanbanCard(id="E-1", class_of_service="expedite")
        errors = validate_card(card)
        self.assertTrue(any("cos_justification" in e for e in errors))

    def test_fixed_date_needs_deadline(self):
        card = KanbanCard(id="F-1", class_of_service="fixed-date")
        errors = validate_card(card)
        self.assertTrue(any("deadline" in e for e in errors))

    def test_score_out_of_range(self):
        card = KanbanCard(id="S-1", value_score=101)
        errors = validate_card(card)
        self.assertTrue(any("value_score" in e for e in errors))

    def test_invalid_action(self):
        card = KanbanCard(id="A-1", action="InvalidAction")
        errors = validate_card(card)
        self.assertTrue(any("action" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
