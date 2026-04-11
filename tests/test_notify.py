#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.notifications.notify import send_telegram_message


class NotifyTest(unittest.TestCase):
    @patch("orc_core.notifications.notify.post_telegram_message")
    @patch("orc_core.notifications.notify.resolve_telegram_credentials", return_value=("token", "chat-id", "env"))
    def test_send_telegram_message_skips_when_disabled(self, _resolve_mock, post_message_mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / ".orc" / "orc.log"
            with patch.dict("os.environ", {"ORC_TELEGRAM_DISABLE": "1"}, clear=False):
                send_telegram_message("hello", log_path)
        post_message_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
