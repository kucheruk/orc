#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orc_core.hooks import ensure_repo_hooks


def _run_hook(script_path: Path, payload: dict, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


class WorktreeHookTaskFileResolutionTest(unittest.TestCase):
    def test_before_submit_reads_task_file_from_orc_task_file_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_dir = root / "base"
            worktree_dir = root / "worktree"
            base_dir.mkdir(parents=True, exist_ok=True)
            worktree_dir.mkdir(parents=True, exist_ok=True)
            ensure_repo_hooks(str(worktree_dir))
            script_path = worktree_dir / ".cursor" / "hooks" / "orc_before_submit.py"

            task_path = base_dir / ".cursor" / "orc-task.json"
            runtime_task_path = base_dir / ".cursor" / "orc-task-runtime.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001",
                        "task_text": "demo",
                        "backlog_path": str(base_dir / "BACKLOG.md"),
                        "conversation_id": "",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_task_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "task_id": "TASK-001",
                        "active_seconds": 15.0,
                        "last_heartbeat_at": 0.0,
                        "run_id": "run-1",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["ORC_TASK_FILE"] = str(task_path)
            env["ORC_TASK_RUNTIME_FILE"] = str(runtime_task_path)
            env["ORC_BASE_WORKSPACE"] = str(base_dir)
            env["ORC_STATS_FILE"] = str(base_dir / "state" / "stats.json")

            result = _run_hook(
                script_path,
                {"conversation_id": "conv-123", "workspace_roots": [str(worktree_dir)]},
                env,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            stored = json.loads(task_path.read_text(encoding="utf-8"))
            self.assertEqual(stored.get("conversation_id"), "conv-123")
            self.assertTrue((base_dir / "state" / "stats.json").exists())

    def test_stop_marks_base_backlog_done_via_orc_task_file_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            base_dir = root / "base"
            worktree_dir = root / "worktree"
            base_dir.mkdir(parents=True, exist_ok=True)
            worktree_dir.mkdir(parents=True, exist_ok=True)
            ensure_repo_hooks(str(worktree_dir))
            script_path = worktree_dir / ".cursor" / "hooks" / "orc_stop.py"

            backlog_path = base_dir / "BACKLOG.md"
            backlog_path.write_text("- [ ] TASK-001 demo\n", encoding="utf-8")

            task_path = base_dir / ".cursor" / "orc-task.json"
            runtime_task_path = base_dir / ".cursor" / "orc-task-runtime.json"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            task_path.write_text(
                json.dumps(
                    {
                        "task_id": "TASK-001",
                        "task_text": "demo",
                        "backlog_path": str(backlog_path),
                        "conversation_id": "conv-123",
                        "created_at": "2026-03-04T00:00:00",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            runtime_task_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "task_id": "TASK-001",
                        "active_seconds": 7.0,
                        "last_heartbeat_at": 0.0,
                        "run_id": "run-1",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            metrics_path = base_dir / "state" / "metrics.json"
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            metrics_path.write_text(
                json.dumps({"tokens_total": 123}, ensure_ascii=False),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["ORC_TASK_FILE"] = str(task_path)
            env["ORC_TASK_RUNTIME_FILE"] = str(runtime_task_path)
            env["ORC_BASE_WORKSPACE"] = str(base_dir)
            env["ORC_STATS_FILE"] = str(base_dir / "state" / "stats.json")
            env["ORC_METRICS_FILE"] = str(metrics_path)

            result = _run_hook(
                script_path,
                {"status": "completed", "conversation_id": "conv-123", "workspace_roots": [str(worktree_dir)]},
                env,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("- [x] TASK-001 demo", backlog_path.read_text(encoding="utf-8"))
            self.assertFalse(task_path.exists())
            self.assertFalse(runtime_task_path.exists())
            stats_payload = json.loads((base_dir / "state" / "stats.json").read_text(encoding="utf-8"))
            self.assertEqual(stats_payload.get("tokens_total"), 123)
            self.assertEqual(stats_payload.get("tokens_by_task", {}).get("TASK-001"), 123)


if __name__ == "__main__":
    unittest.main()
