#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.task_contract import extract_task_id, parse_task_line, render_task_line_with_mark


class TaskContractTest(unittest.TestCase):
    def test_extract_task_id_supports_bold_and_colon(self) -> None:
        self.assertEqual(extract_task_id("**ORC-REF-001:** Централизовать контракт"), "ORC-REF-001")
        self.assertEqual(extract_task_id("ORC_REF_002 Сделать что-то"), "ORC_REF_002")
        self.assertIsNone(extract_task_id("без идентификатора"))

    def test_parse_task_line_extracts_structured_fields(self) -> None:
        parsed = parse_task_line("- [ ] **ORC-REF-001:** Централизовать parser")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.mark, " ")
        self.assertEqual(parsed.task_id, "ORC-REF-001")
        self.assertEqual(parsed.text, "**ORC-REF-001:** Централизовать parser")

    def test_render_task_line_with_mark_preserves_text(self) -> None:
        parsed = parse_task_line("  - [ ] ORC-REF-001 Централизовать parser")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        rendered = render_task_line_with_mark(parsed, "x")
        self.assertEqual(rendered, "  - [x] ORC-REF-001 Централизовать parser")


if __name__ == "__main__":
    unittest.main()
