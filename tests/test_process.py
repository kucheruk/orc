#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.process import acquire_lock, release_lock


class ProcessLockTest(unittest.TestCase):
    def test_acquire_lock_writes_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / ".orc" / "orc.lock"
            log_path = root / ".orc" / "orc.log"
            acquire_lock(lock_path, log_path)
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertIn("pid", payload)
            self.assertIn("started_at", payload)
            release_lock(lock_path, log_path)

    @patch("orc_core.process.is_pid_alive", return_value=False)
    def test_acquire_lock_replaces_stale_lock(self, _alive_mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / ".orc" / "orc.lock"
            log_path = root / ".orc" / "orc.log"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(json.dumps({"pid": 123, "started_at": "2026-01-01T00:00:00"}, ensure_ascii=False), encoding="utf-8")
            acquire_lock(lock_path, log_path)
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertNotEqual(int(payload.get("pid") or 0), 123)
            release_lock(lock_path, log_path)

    @patch("orc_core.process.is_pid_alive", return_value=True)
    def test_acquire_lock_fails_when_active_lock_exists(self, _alive_mock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / ".orc" / "orc.lock"
            log_path = root / ".orc" / "orc.log"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(json.dumps({"pid": 555, "started_at": "2026-01-01T00:00:00"}, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(SystemExit) as exc_info:
                acquire_lock(lock_path, log_path)
            self.assertEqual(exc_info.exception.code, 3)


if __name__ == "__main__":
    unittest.main()
