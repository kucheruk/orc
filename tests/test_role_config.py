#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.cli.model_selector import DEFAULT_MODEL
from orc_core.cli.role_config import (
    ROLE_CODER,
    ROLE_HANDOFF,
    ROLE_MERGE_EXPERT,
    RoleProfileRegistry,
)


class RoleProfileRegistryTest(unittest.TestCase):
    def test_load_overrides_returns_empty_when_missing(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(registry.load_overrides(tmpdir), {})

    def test_update_override_roundtrip_for_coder(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry.update_override(tmpdir, ROLE_CODER, enabled=False, model="sonnet-4.5", prompt="custom coder prompt")
            resolved = registry.resolve_role(tmpdir, ROLE_CODER)

        self.assertFalse(resolved.enabled)
        self.assertEqual(resolved.model, "sonnet-4.5")
        self.assertEqual(resolved.prompt, "custom coder prompt")

    def test_role_defaults_match_expected_enabled_and_toggleability(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            handoff = registry.resolve_role(tmpdir, ROLE_HANDOFF)
            coder = registry.resolve_role(tmpdir, ROLE_CODER)
            merge_expert = registry.resolve_role(tmpdir, ROLE_MERGE_EXPERT)

        self.assertTrue(coder.enabled)
        self.assertTrue(coder.can_toggle_enabled)
        self.assertTrue(handoff.enabled)
        self.assertFalse(handoff.can_toggle_enabled)
        self.assertFalse(merge_expert.enabled)
        self.assertFalse(merge_expert.can_toggle_enabled)

    def test_resolve_role_priority_cli_override_then_saved_then_default(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry.update_override(tmpdir, ROLE_CODER, model="o3", prompt="saved prompt")
            cli_prompt_file = Path(tmpdir) / "cli_prompt.txt"
            cli_prompt_file.write_text("cli prompt", encoding="utf-8")
            resolved = registry.resolve_role(
                tmpdir,
                ROLE_CODER,
                cli_model="gpt-5.3-codex",
                cli_prompt_path=str(cli_prompt_file),
            )

        self.assertEqual(resolved.model, "gpt-5.3-codex")
        self.assertEqual(resolved.prompt, "cli prompt")

    def test_resolve_role_uses_defaults_without_overrides(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            resolved = registry.resolve_role(tmpdir, ROLE_CODER)
        self.assertEqual(resolved.model, DEFAULT_MODEL)
        # ROLE_CODER is config-only in kanban mode — no prompt file
        self.assertIn("kanban mode", resolved.prompt)

    def test_resolve_merge_expert_role_uses_prompt_file_by_default(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            resolved = registry.resolve_role(tmpdir, ROLE_MERGE_EXPERT)
        self.assertEqual(resolved.model, DEFAULT_MODEL)
        self.assertIn("эксперт по разрешению merge-конфликтов", resolved.prompt)


if __name__ == "__main__":
    unittest.main()
