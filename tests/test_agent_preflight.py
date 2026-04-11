#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from orc_core.cli.agent_preflight import AgentNotInstalledError, ensure_agent_installed


class AgentPreflightTest(unittest.TestCase):
    @patch("orc_core.backends.cursor.shutil.which", return_value="/usr/local/bin/agent")
    def test_ensure_agent_installed_passes_when_binary_exists(self, _which) -> None:
        ensure_agent_installed()

    @patch("orc_core.backends.cursor.shutil.which", return_value=None)
    def test_ensure_agent_installed_raises_with_install_hint(self, _which) -> None:
        with self.assertRaises(AgentNotInstalledError) as ctx:
            ensure_agent_installed()
        message = str(ctx.exception)
        self.assertIn("agent", message)
        self.assertIn("Install Cursor CLI", message)
        self.assertIn("agent --version", message)


if __name__ == "__main__":
    unittest.main()
