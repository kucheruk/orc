#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.model_selector import DEFAULT_MODEL
from orc_core.role_config import (
    ROLE_ANALYSIS_PLANNING,
    ROLE_CODE_REVIEW,
    ROLE_CODER,
    ROLE_DESIGN,
    ROLE_HANDOFF,
    ROLE_MERGE_EXPERT,
    ROLE_SUPERVISOR,
    ROLE_TESTER,
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

    def test_non_toggle_role_ignores_enabled_override(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry.update_override(tmpdir, ROLE_SUPERVISOR, enabled=True, model="gpt-5.3-codex")
            resolved = registry.resolve_role(tmpdir, ROLE_SUPERVISOR)

        self.assertFalse(resolved.enabled)
        self.assertEqual(resolved.model, "gpt-5.3-codex")

    def test_sdlc_defaults_match_expected_enabled_and_toggleability(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            planning = registry.resolve_role(tmpdir, ROLE_ANALYSIS_PLANNING)
            design = registry.resolve_role(tmpdir, ROLE_DESIGN)
            review = registry.resolve_role(tmpdir, ROLE_CODE_REVIEW)
            testing = registry.resolve_role(tmpdir, ROLE_TESTER)
            handoff = registry.resolve_role(tmpdir, ROLE_HANDOFF)
            coder = registry.resolve_role(tmpdir, ROLE_CODER)

        self.assertFalse(planning.enabled)
        self.assertTrue(planning.can_toggle_enabled)
        self.assertFalse(design.enabled)
        self.assertTrue(design.can_toggle_enabled)
        self.assertFalse(review.enabled)
        self.assertTrue(review.can_toggle_enabled)
        self.assertFalse(testing.enabled)
        self.assertTrue(testing.can_toggle_enabled)
        self.assertTrue(coder.enabled)
        self.assertTrue(coder.can_toggle_enabled)
        self.assertTrue(handoff.enabled)
        self.assertFalse(handoff.can_toggle_enabled)

    def test_update_override_roundtrip_for_planning_and_review(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            registry.update_override(
                tmpdir,
                ROLE_ANALYSIS_PLANNING,
                enabled=False,
                model="sonnet-4.5",
                prompt="custom planning prompt",
            )
            registry.update_override(
                tmpdir,
                ROLE_CODE_REVIEW,
                enabled=False,
                model="o3",
                prompt="custom review prompt",
            )
            planning = registry.resolve_role(tmpdir, ROLE_ANALYSIS_PLANNING)
            review = registry.resolve_role(tmpdir, ROLE_CODE_REVIEW)

        self.assertFalse(planning.enabled)
        self.assertEqual(planning.model, "sonnet-4.5")
        self.assertEqual(planning.prompt, "custom planning prompt")
        self.assertFalse(review.enabled)
        self.assertEqual(review.model, "o3")
        self.assertEqual(review.prompt, "custom review prompt")

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
        self.assertIn("Роль: эксперт-программист", resolved.prompt)

    def test_resolve_merge_expert_role_uses_prompt_file_by_default(self) -> None:
        registry = RoleProfileRegistry()
        with tempfile.TemporaryDirectory() as tmpdir:
            resolved = registry.resolve_role(tmpdir, ROLE_MERGE_EXPERT)
        self.assertEqual(resolved.model, DEFAULT_MODEL)
        self.assertIn("эксперт по разрешению merge-конфликтов", resolved.prompt)


if __name__ == "__main__":
    unittest.main()
