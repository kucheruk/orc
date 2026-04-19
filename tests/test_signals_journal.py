#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the signal journal and digest."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from orc_core.signals import SignalKind, emit_signal, load_since, format_digest


class EmitSignalTest(unittest.TestCase):
    def test_emit_writes_append_only_json_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.jsonl"
            emit_signal(
                SignalKind.CARD_DONE, "pipeline_complete",
                path=path, task_id="T-1",
                context={"role": "integrator", "elapsed_s": 120},
            )
            emit_signal(
                SignalKind.CARD_BLOCKED, "token_budget_exhausted",
                path=path, task_id="T-2",
                context={"tokens_spent": 500000, "token_budget": 400000},
            )
            lines = path.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            self.assertEqual(first["kind"], "card.done")
            self.assertEqual(first["task_id"], "T-1")
            self.assertEqual(first["context"]["role"], "integrator")
            second = json.loads(lines[1])
            self.assertEqual(second["kind"], "card.blocked")
            self.assertEqual(second["reason"], "token_budget_exhausted")
            self.assertIn("ts", first)
            self.assertIn("pid", first)

    def test_emit_never_raises_even_on_bad_path(self):
        # Path pointing into a file (not a directory) → open-append would fail.
        with tempfile.NamedTemporaryFile() as f:
            bad_path = Path(f.name) / "signals.jsonl"
            emit_signal(SignalKind.ORC_STARTUP, "bootstrap", path=bad_path)
            # If we got here without exception, the contract holds.

    def test_emit_resolves_no_workdir_silently(self):
        # No workdir, no path, no env → should noop, not crash.
        import os
        orig = os.environ.pop("ORC_WORKSPACE", None)
        try:
            emit_signal(SignalKind.ORC_STARTUP, "bootstrap")
        finally:
            if orig is not None:
                os.environ["ORC_WORKSPACE"] = orig

    def test_coerce_non_serializable_in_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.jsonl"
            emit_signal(
                SignalKind.ATTEMPT_DISCARDED, "stale_fingerprint",
                path=path, task_id="T-3",
                context={"workspace": Path("/tmp/x"), "nested": {"p": Path("/a")}},
            )
            d = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(d["context"]["workspace"], "/tmp/x")
            self.assertEqual(d["context"]["nested"]["p"], "/a")


class LoadSinceTest(unittest.TestCase):
    def test_filters_by_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.jsonl"
            old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
            fresh = datetime.now(timezone.utc).isoformat(timespec="seconds")
            path.write_text(
                json.dumps({"ts": old, "kind": "card.done", "task_id": "OLD"}) + "\n" +
                json.dumps({"ts": fresh, "kind": "card.done", "task_id": "NEW"}) + "\n"
            )
            got = load_since(path, seconds=1200)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["task_id"], "NEW")

    def test_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.jsonl"
            fresh = datetime.now(timezone.utc).isoformat(timespec="seconds")
            path.write_text(
                "not json\n" +
                json.dumps({"ts": fresh, "kind": "card.done", "task_id": "X"}) + "\n"
            )
            got = load_since(path, seconds=1200)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["task_id"], "X")

    def test_missing_file_returns_empty(self):
        self.assertEqual(load_since(Path("/nonexistent/x.jsonl"), seconds=60), [])


class DigestTest(unittest.TestCase):
    def _sig(self, kind: str, **fields):
        return {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kind": kind,
            "reason": fields.pop("reason", ""),
            "task_id": fields.pop("task_id", ""),
            "context": fields.pop("context", {}),
            "pid": 1,
        }

    def test_empty_window(self):
        out = format_digest([], window_seconds=1200)
        self.assertIn("No signals", out)

    def test_renders_pipeline_section(self):
        sigs = [
            self._sig("card.done", task_id="A", reason="pipeline_complete"),
            self._sig("card.done", task_id="B", reason="pipeline_complete"),
            self._sig("card.blocked", task_id="C", reason="token_budget_exhausted",
                      context={"tokens_spent": 500000, "token_budget": 400000, "role": "coder"}),
        ]
        out = format_digest(sigs, window_seconds=1200)
        self.assertIn("Pipeline", out)
        self.assertIn("2 → Done", out)
        self.assertIn("A, B", out)
        self.assertIn("C — token_budget_exhausted", out)
        self.assertIn("500000/400000", out)

    def test_renders_problems_section(self):
        sigs = [
            self._sig("attempt.validation_failed", task_id="X",
                      context={"role": "coder"}, reason="launch fingerprint action is stale"),
            self._sig("attempt.validation_failed", task_id="X",
                      context={"role": "coder"}, reason="same"),
            self._sig("attempt.max_restarts", task_id="Y", reason="restart_policy_exceeded"),
            self._sig("attempt.discarded", task_id="Z", reason="stale_fingerprint",
                      context={"tokens": 42_000}),
        ]
        out = format_digest(sigs, window_seconds=1200)
        self.assertIn("Problems", out)
        self.assertIn("X (coder) ×2", out)
        self.assertIn("Y", out)
        self.assertIn("42,000", out)

    def test_teamlead_section_groups_by_kind(self):
        sigs = [
            self._sig("teamlead.health_check", reason="DEADLOCK: x"),
            self._sig("teamlead.health_check", reason="DEADLOCK: x"),
            self._sig("teamlead.arbitration", task_id="Q"),
        ]
        out = format_digest(sigs, window_seconds=1200)
        self.assertIn("2 health checks", out)
        self.assertIn("1 arbitrations", out)
        self.assertIn("Q", out)

    def test_orc_section_sorted_chronologically(self):
        base = datetime.now(timezone.utc)
        sigs = [
            {"ts": (base + timedelta(seconds=10)).isoformat(timespec="seconds"),
             "kind": "orc.shutdown", "reason": "exit_code=0", "task_id": "", "context": {}, "pid": 1},
            {"ts": base.isoformat(timespec="seconds"),
             "kind": "orc.startup", "reason": "bootstrap", "task_id": "", "context": {}, "pid": 1},
        ]
        out = format_digest(sigs, window_seconds=1200)
        startup_pos = out.index("orc.startup")
        shutdown_pos = out.index("orc.shutdown")
        self.assertLess(startup_pos, shutdown_pos)


if __name__ == "__main__":
    unittest.main()
