#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orc_core.process import acquire_lock, kill_orphan_project_processes, release_lock


class _FakeOrphanProcess:
    def __init__(
        self,
        *,
        pid: int,
        ppid: int,
        cwd: str,
        cmdline: list[str],
        name: str = "python3",
        create_time: float = 100.0,
        env: dict[str, str] | None = None,
    ) -> None:
        self.pid = pid
        self._env = dict(env or {})
        self.info = {
            "pid": pid,
            "ppid": ppid,
            "cwd": cwd,
            "cmdline": list(cmdline),
            "name": name,
            "create_time": create_time,
        }
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def environ(self) -> dict[str, str]:
        return dict(self._env)


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

    def test_acquire_lock_does_not_use_path_write_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / ".orc" / "orc.lock"
            log_path = root / ".orc" / "orc.log"
            with patch.object(Path, "write_text", side_effect=RuntimeError("Path.write_text should not be used")):
                acquire_lock(lock_path, log_path)
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertIn("pid", payload)
            self.assertIn("started_at", payload)


class OrphanSweepTest(unittest.TestCase):
    @patch("orc_core.process.log_event")
    @patch("orc_core.process.psutil.wait_procs", return_value=([], []))
    @patch("orc_core.process.os.getpid", return_value=999_999)
    def test_orphan_sweep_does_not_match_neighbor_prefix_path(self, _pid_mock, _wait_mock, _log_mock) -> None:
        workspace = "/repo/orc"
        neighbor = _FakeOrphanProcess(
            pid=1001,
            ppid=1,
            cwd="/repo/orc_two",
            cmdline=["python3", "/repo/orc_two/.cursor/hooks/orc_stop.py"],
        )
        with patch("orc_core.process.psutil.process_iter", return_value=[neighbor]):
            killed = kill_orphan_project_processes(
                workspace,
                Path("/tmp/orc.log"),
                label="test",
                command_markers=("python3", "orc_stop.py"),
            )
        self.assertEqual(killed, [])
        self.assertFalse(neighbor.terminated)

    @patch("orc_core.process.log_event")
    @patch("orc_core.process.psutil.wait_procs", return_value=([], []))
    @patch("orc_core.process.os.getpid", return_value=999_999)
    def test_orphan_sweep_matches_workspace_subdirectory(self, _pid_mock, _wait_mock, _log_mock) -> None:
        workspace = "/repo/orc"
        owned = _FakeOrphanProcess(
            pid=1002,
            ppid=1,
            cwd="/repo/orc/.cursor/hooks",
            cmdline=["python3", "/repo/orc/.cursor/hooks/orc_stop.py"],
        )
        with patch("orc_core.process.psutil.process_iter", return_value=[owned]):
            killed = kill_orphan_project_processes(
                workspace,
                Path("/tmp/orc.log"),
                label="test",
                command_markers=("python3", "orc_stop.py"),
            )
        self.assertEqual(killed, [1002])
        self.assertTrue(owned.terminated)

    @patch("orc_core.process.log_event")
    @patch("orc_core.process.psutil.wait_procs", return_value=([], []))
    @patch("orc_core.process.os.getpid", return_value=999_999)
    def test_orphan_sweep_matches_by_orc_run_token(self, _pid_mock, _wait_mock, _log_mock) -> None:
        token = "run-token-1"
        token_proc = _FakeOrphanProcess(
            pid=1003,
            ppid=1,
            cwd="/tmp/elsewhere",
            cmdline=["python3", "worker.py"],
            env={"ORC_RUN_TOKEN": token},
        )
        with patch("orc_core.process.psutil.process_iter", return_value=[token_proc]):
            killed = kill_orphan_project_processes(
                "/repo/orc",
                Path("/tmp/orc.log"),
                label="test",
                command_markers=("agent",),
                run_token=token,
            )
        self.assertEqual(killed, [1003])
        self.assertTrue(token_proc.terminated)

    @patch("orc_core.process.log_event")
    @patch("orc_core.process.psutil.wait_procs", return_value=([], []))
    @patch("orc_core.process.os.getpid", return_value=999_999)
    def test_orphan_sweep_does_not_match_token_mismatch(self, _pid_mock, _wait_mock, _log_mock) -> None:
        token_proc = _FakeOrphanProcess(
            pid=1004,
            ppid=1,
            cwd="/tmp/elsewhere",
            cmdline=["python3", "worker.py"],
            env={"ORC_RUN_TOKEN": "another-token"},
        )
        with patch("orc_core.process.psutil.process_iter", return_value=[token_proc]):
            killed = kill_orphan_project_processes(
                "/repo/orc",
                Path("/tmp/orc.log"),
                label="test",
                command_markers=("agent",),
                run_token="run-token-1",
            )
        self.assertEqual(killed, [])
        self.assertFalse(token_proc.terminated)

    @patch("orc_core.process.log_event")
    @patch("orc_core.process.psutil.wait_procs", return_value=([], []))
    @patch("orc_core.process.os.getpid", return_value=999_999)
    def test_orphan_sweep_does_not_treat_relative_cmdline_as_workspace_path(self, _pid_mock, _wait_mock, _log_mock) -> None:
        workspace = str(Path.cwd())
        foreign = _FakeOrphanProcess(
            pid=1005,
            ppid=1,
            cwd="/tmp/foreign",
            cmdline=["pytest", "-k", "test_something"],
        )
        with patch("orc_core.process.psutil.process_iter", return_value=[foreign]):
            killed = kill_orphan_project_processes(
                workspace,
                Path("/tmp/orc.log"),
                label="test",
                command_markers=("pytest",),
            )
        self.assertEqual(killed, [])
        self.assertFalse(foreign.terminated)


if __name__ == "__main__":
    unittest.main()
