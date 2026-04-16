#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path

from orc_core.agents.results.io import build_result_file_path, build_result_run_id
from orc_core.agents.results.prompt_contract import build_result_contract_block
from orc_core.agents.results.schema import (
    PAYLOAD_CARD_UPDATE,
    PAYLOAD_INCIDENT_TRIAGE,
    PAYLOAD_TEAMLEAD_ACTIONS,
    load_structured_agent_result,
    parse_structured_agent_result,
    validate_structured_agent_result,
)


class StructuredAgentResultsTest(unittest.TestCase):
    def test_parse_card_update_payload(self):
        result = parse_structured_agent_result({
            "schema_version": 1,
            "payload_kind": PAYLOAD_CARD_UPDATE,
            "role": "coder",
            "run_id": "TASK-1:implementation:attempt-1",
            "summary": "done",
            "payload": {
                "task_id": "TASK-1",
                "launch_fingerprint": {
                    "stage": "4_Coding",
                    "action": "Coding",
                    "file_path": "tasks/4_Coding/TASK-1.md",
                    "state_version": 7,
                },
                "next_action": "Reviewing",
                "field_updates": {"title": "Updated"},
                "section_updates": {"implementation_notes": "Implemented."},
                "feedback_append": "- [x] verified",
            },
        })
        self.assertEqual(result.payload.task_id, "TASK-1")
        self.assertEqual(result.payload.launch_fingerprint.state_version, 7)

    def test_parse_teamlead_and_incident_payloads(self):
        teamlead = parse_structured_agent_result({
            "schema_version": 1,
            "payload_kind": PAYLOAD_TEAMLEAD_ACTIONS,
            "role": "teamlead",
            "run_id": "tl:health:attempt-1",
            "summary": "adjusted WIP",
            "payload": {
                "actions": [
                    {"type": "set_wip_limit", "stage": "5_Review", "limit": 2, "reason": "unblock flow"},
                ],
            },
        })
        incident = parse_structured_agent_result({
            "schema_version": 1,
            "payload_kind": PAYLOAD_INCIDENT_TRIAGE,
            "role": "teamlead_triage",
            "run_id": "incident:triage:attempt-1",
            "summary": "project bug",
            "payload": {
                "classification": "project",
                "target_role": "coder",
                "fix_title": "Fix failing test",
                "body": "# 1. Product Requirements\n\nFix it.\n",
            },
        })
        self.assertEqual(teamlead.payload.actions[0].type, "set_wip_limit")
        self.assertEqual(incident.payload.classification, "project")

    def test_validate_expected_envelope_fields(self):
        result = parse_structured_agent_result({
            "schema_version": 1,
            "payload_kind": PAYLOAD_TEAMLEAD_ACTIONS,
            "role": "teamlead",
            "run_id": "tl:directive:attempt-2",
            "summary": "",
            "payload": {"actions": []},
        })
        validate_structured_agent_result(
            result,
            expected_run_id="tl:directive:attempt-2",
            expected_role="teamlead",
            expected_payload_kind=PAYLOAD_TEAMLEAD_ACTIONS,
        )
        with self.assertRaises(ValueError):
            validate_structured_agent_result(result, expected_run_id="other")

    def test_load_from_disk_and_build_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            result_path = build_result_file_path(
                run_root,
                task_id="TASK-55",
                stage_id="5_Review",
                attempt=3,
            )
            result_path.write_text(json.dumps({
                "schema_version": 1,
                "payload_kind": PAYLOAD_TEAMLEAD_ACTIONS,
                "role": "teamlead",
                "run_id": build_result_run_id(task_id="TASK-55", stage_id="5_Review", attempt=3),
                "summary": "ok",
                "payload": {"actions": []},
            }), encoding="utf-8")
            loaded = load_structured_agent_result(result_path)
            self.assertEqual(loaded.run_id, "TASK-55:5_Review:attempt-3")
            self.assertTrue(result_path.name.endswith("attempt-3.json"))

    def test_prompt_contract_mentions_file_run_id_and_payload_kind(self):
        block = build_result_contract_block(
            result_file="/tmp/result.json",
            run_id="TASK-1:implementation:attempt-1",
            payload_kind=PAYLOAD_CARD_UPDATE,
            required_payload_keys=("task_id", "launch_fingerprint"),
        )
        self.assertIn("/tmp/result.json", block)
        self.assertIn("TASK-1:implementation:attempt-1", block)
        self.assertIn(PAYLOAD_CARD_UPDATE, block)


if __name__ == "__main__":
    unittest.main()
