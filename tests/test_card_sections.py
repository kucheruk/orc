#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.board.card_sections import (
    merge_section_updates,
    new_card_body,
    parse_card_sections,
    render_card_sections,
)


class CardSectionsTest(unittest.TestCase):
    def test_roundtrip_empty_layout(self):
        body = new_card_body()
        sections = parse_card_sections(body)
        self.assertEqual(render_card_sections(sections), body)

    def test_replaces_named_section_and_appends_feedback(self):
        body = merge_section_updates(
            new_card_body(),
            section_updates={"technical_design": "Use a worker-specific contract."},
            feedback_append="- [ ] Verify result artifact parsing",
        )
        sections = parse_card_sections(body)
        self.assertEqual(sections["technical_design"], "Use a worker-specific contract.")
        self.assertEqual(sections["feedback_checklist"], "- [ ] Verify result artifact parsing")

        updated = merge_section_updates(
            body,
            section_updates={"implementation_notes": "Implemented structured sections."},
            feedback_append="- [x] Added section helpers",
        )
        sections = parse_card_sections(updated)
        self.assertEqual(sections["implementation_notes"], "Implemented structured sections.")
        self.assertEqual(
            sections["feedback_checklist"],
            "- [ ] Verify result artifact parsing\n\n- [x] Added section helpers",
        )

    def test_legacy_body_is_preserved_in_implementation_notes(self):
        sections = parse_card_sections("legacy body without headers")
        self.assertEqual(sections["implementation_notes"], "legacy body without headers")

    def test_unknown_section_key_raises(self):
        with self.assertRaises(ValueError):
            merge_section_updates(new_card_body(), section_updates={"unknown": "value"})


if __name__ == "__main__":
    unittest.main()
