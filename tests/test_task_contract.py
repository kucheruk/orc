#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.board.task_contract import extract_task_id


class TaskContractTest(unittest.TestCase):
    def test_extract_task_id_supports_bold_colon_and_terminal_id(self) -> None:
        self.assertEqual(extract_task_id("**ORC-REF-001:** Централизовать контракт"), "ORC-REF-001")
        self.assertEqual(extract_task_id("ORC_REF_002 Сделать что-то"), "ORC_REF_002")
        self.assertEqual(extract_task_id("TASK-100"), "TASK-100")
        self.assertIsNone(extract_task_id("без идентификатора"))

    def test_extract_task_id_does_not_match_middle_of_text(self) -> None:
        self.assertIsNone(extract_task_id("Описание ORC-REF-123 в середине строки"))


if __name__ == "__main__":
    unittest.main()
