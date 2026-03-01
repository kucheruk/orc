#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.model_selector import DEFAULT_MODEL
from orc_core.role_config import ROLE_CODER, ROLE_SUPERVISOR, RoleProfileRegistry


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


if __name__ == "__main__":
    unittest.main()
