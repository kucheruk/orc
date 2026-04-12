#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.infra.io.atomic_io import write_json_atomic, write_text_atomic


class AtomicIoTest(unittest.TestCase):
    def test_write_text_atomic_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.txt"
            write_text_atomic(path, "hello", encoding="utf-8")
            self.assertEqual(path.read_text(encoding="utf-8"), "hello")

    def test_write_json_atomic_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"
            payload = {"task_id": "TASK-001", "restart_count": 3}
            write_json_atomic(path, payload, ensure_ascii=False, indent=2)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)

    def test_write_json_atomic_leaves_no_temp_file_on_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"
            with patch("orc_core.infra.io.atomic_io.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    write_json_atomic(path, {"ok": True})
            leftovers = [p.name for p in path.parent.iterdir() if p.is_file()]
            self.assertEqual(leftovers, [])

    def test_write_json_atomic_prevents_partial_json_during_rapid_rewrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            write_json_atomic(path, {"seq": 0})
            stop_event = threading.Event()
            decode_errors = []

            def writer() -> None:
                for i in range(1, 600):
                    write_json_atomic(path, {"seq": i, "payload": "x" * (i % 17 + 1)})
                stop_event.set()

            def reader() -> None:
                while not stop_event.is_set():
                    try:
                        json.loads(path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as exc:
                        decode_errors.append(exc)

            writer_thread = threading.Thread(target=writer)
            reader_thread = threading.Thread(target=reader)
            writer_thread.start()
            reader_thread.start()
            writer_thread.join()
            stop_event.set()
            reader_thread.join()

            self.assertEqual(decode_errors, [])


if __name__ == "__main__":
    unittest.main()
