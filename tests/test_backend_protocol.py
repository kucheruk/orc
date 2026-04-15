#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.backends.backend import Backend, SUPPORTED_BACKENDS, get_backend
from orc_core.backends.cursor import CursorBackend
from orc_core.backends.claude import ClaudeBackend
from orc_core.backends.codex import CodexBackend


class GetBackendFactoryTest(unittest.TestCase):
    def test_cursor_is_default(self) -> None:
        backend = get_backend()
        self.assertIsInstance(backend, CursorBackend)

    def test_get_cursor(self) -> None:
        self.assertIsInstance(get_backend("cursor"), CursorBackend)

    def test_get_claude(self) -> None:
        self.assertIsInstance(get_backend("claude"), ClaudeBackend)

    def test_get_codex(self) -> None:
        self.assertIsInstance(get_backend("codex"), CodexBackend)

    def test_unknown_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_backend("unknown")

    def test_supported_backends_tuple(self) -> None:
        self.assertEqual(SUPPORTED_BACKENDS, ("cursor", "claude", "codex"))


class ProtocolComplianceTest(unittest.TestCase):
    def test_cursor_implements_protocol(self) -> None:
        self.assertIsInstance(CursorBackend(), Backend)

    def test_claude_implements_protocol(self) -> None:
        self.assertIsInstance(ClaudeBackend(), Backend)

    def test_codex_implements_protocol(self) -> None:
        self.assertIsInstance(CodexBackend(), Backend)


class BackendPropertiesTest(unittest.TestCase):
    def _check_backend_properties(self, backend: Backend, expected_name: str, expected_binary: str) -> None:
        self.assertEqual(backend.name, expected_name)
        self.assertEqual(backend.cli_binary, expected_binary)
        self.assertIsInstance(backend.default_model(), str)
        self.assertTrue(len(backend.default_model()) > 0)

    def test_cursor_properties(self) -> None:
        self._check_backend_properties(CursorBackend(), "cursor", "agent")

    def test_claude_properties(self) -> None:
        self._check_backend_properties(ClaudeBackend(), "claude", "claude")

    def test_codex_properties(self) -> None:
        self._check_backend_properties(CodexBackend(), "codex", "codex")


class ListModelsCmdTest(unittest.TestCase):
    def test_cursor_has_list_models_cmd(self) -> None:
        cmd = CursorBackend().list_models_cmd()
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd, ["agent", "--list-models"])

    def test_claude_returns_none(self) -> None:
        self.assertIsNone(ClaudeBackend().list_models_cmd())

    def test_codex_returns_none(self) -> None:
        self.assertIsNone(CodexBackend().list_models_cmd())


if __name__ == "__main__":
    unittest.main()
