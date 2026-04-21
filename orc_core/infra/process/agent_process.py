#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent subprocess lifecycle: spawn, stream, stop."""

from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path
from typing import Callable, Mapping, Optional

from ...log import log_event
from .process import kill_process_tree
from .process_groups import resolve_process_group_id, subprocess_group_spawn_kwargs, terminate_process_group

STREAM_READER_LIMIT_BYTES = 32 * 1024 * 1024


class _ProcessProxy:
    """Lightweight thread-safe holder for pid/returncode visible outside the asyncio loop."""

    __slots__ = ("pid", "returncode")

    def __init__(self) -> None:
        self.pid: Optional[int] = None
        self.returncode: Optional[int] = None

    def poll(self) -> Optional[int]:
        return self.returncode


class AgentProcess:
    """Manages an agent subprocess lifecycle: spawn in asyncio loop, stream output, stop.

    Calls *on_stdout_line* and *on_stderr_line* for each decoded line.
    """

    def __init__(
        self,
        *,
        agent_cmd: list[str],
        workdir: str,
        log_path: Path,
        child_env_overrides: Mapping[str, str] | None = None,
        run_token: str = "",
        on_stdout_line: Callable[[str], None] | None = None,
        on_stderr_line: Callable[[str], None] | None = None,
        on_process_exit: Callable[[int], None] | None = None,
        spawn_timeout: float = 20.0,
    ) -> None:
        self._agent_cmd = list(agent_cmd)
        self.workdir = workdir
        self.log_path = log_path
        self._child_env_overrides = {
            str(k): str(v) for k, v in (child_env_overrides or {}).items()
        }
        self._run_token = run_token
        self._on_stdout = on_stdout_line
        self._on_stderr = on_stderr_line
        self._on_exit = on_process_exit

        self.proc = _ProcessProxy()
        self.init_pid: Optional[int] = None
        self.process_group_id: Optional[int] = None
        self.last_output_time = time.time()

        self._stop = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._spawned = threading.Event()
        self._spawn_error: Optional[BaseException] = None
        # Async event on the worker loop, set from the main thread when stop()
        # is called — lets _read_stream wake out of a blocking readline() even
        # when the child process hasn't closed its pipes yet.
        self._stop_async: Optional[asyncio.Event] = None

        self._runner_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._runner_thread.start()
        if not self._spawned.wait(timeout=spawn_timeout):
            raise RuntimeError("Failed to start async agent subprocess")
        if self._spawn_error is not None:
            raise self._spawn_error

    # ── Public API ──────────────────────────────────────────────

    def refresh_status(self) -> Optional[int]:
        proc = self._proc
        if proc is None:
            return self.proc.returncode
        returncode = proc.returncode
        if returncode is not None:
            self.proc.returncode = returncode
        return self.proc.returncode

    def stop(self) -> None:
        self._stop.set()
        root_pid = self.init_pid or self.proc.pid
        if isinstance(root_pid, int) and root_pid > 0 and self.proc.returncode is None:
            if not terminate_process_group(
                self.process_group_id, self.log_path, label="agent-process-stop",
            ):
                kill_process_tree(root_pid, self.log_path, label="agent-process-stop")
        loop = self._loop
        if loop is not None and not loop.is_closed():
            try:
                # Wake readers sleeping on readline() even if process-group
                # termination didn't close the pipes (rare edge cases on
                # macOS or when PGID resolution returned None).
                def _set_stop() -> None:
                    if self._stop_async is not None and not self._stop_async.is_set():
                        self._stop_async.set()

                loop.call_soon_threadsafe(_set_stop)
            except RuntimeError:
                pass
        if self._runner_thread.is_alive():
            self._runner_thread.join(timeout=2.0)

    # ── Internal ────────────────────────────────────────────────

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._spawn_and_stream())
        finally:
            self._loop.close()

    async def _spawn_and_stream(self) -> None:
        self._stop_async = asyncio.Event()
        try:
            child_env = os.environ.copy()
            if self._run_token:
                child_env["ORC_RUN_TOKEN"] = self._run_token
            child_env.update(self._child_env_overrides)
            self._proc = await asyncio.create_subprocess_exec(
                *self._agent_cmd,
                cwd=self.workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=STREAM_READER_LIMIT_BYTES,
                env=child_env,
                **subprocess_group_spawn_kwargs(),
            )
        except Exception as exc:
            self._spawn_error = exc
            self._spawned.set()
            log_event(self.log_path, "ERROR", "failed to spawn async subprocess", error=str(exc))
            raise
        self.proc.pid = self._proc.pid
        self.init_pid = self._proc.pid
        self.process_group_id = resolve_process_group_id(self._proc.pid)
        self._spawned.set()
        if self._proc.stdout is None or self._proc.stderr is None:
            self.proc.returncode = 1
            return
        stdout_task = asyncio.create_task(self._read_stream(self._proc.stdout, self._on_stdout, "stdout"))
        stderr_task = asyncio.create_task(self._read_stream(self._proc.stderr, self._on_stderr, "stderr"))
        await self._proc.wait()
        self.proc.returncode = self._proc.returncode
        if self._on_exit is not None:
            self._on_exit(int(self.proc.returncode or 0))
        # Cancel reader tasks — process is dead, don't wait for pipe drain forever
        for task in (stdout_task, stderr_task):
            if not task.done():
                task.cancel()
        reader_results = await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        for stream_name, result in zip(("stdout", "stderr"), reader_results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                log_event(
                    self.log_path, "ERROR", "stream reader task failed",
                    stream=stream_name, error=str(result),
                    exception_type=type(result).__name__,
                )

    async def _read_stream(
        self,
        stream: asyncio.StreamReader,
        callback: Callable[[str], None] | None,
        name: str,
    ) -> None:
        stop_async = self._stop_async
        try:
            while not self._stop.is_set():
                read_task = asyncio.create_task(stream.readline())
                waiters = [read_task]
                stop_task: Optional[asyncio.Task] = None
                if stop_async is not None:
                    stop_task = asyncio.create_task(stop_async.wait())
                    waiters.append(stop_task)
                done, pending = await asyncio.wait(
                    waiters, return_when=asyncio.FIRST_COMPLETED,
                )
                if stop_task is not None and stop_task in done:
                    # Stop requested: cancel the pending readline so we don't
                    # keep the loop alive waiting for pipe close.
                    if not read_task.done():
                        read_task.cancel()
                    for p in pending:
                        if p is not read_task:
                            p.cancel()
                    return
                if stop_task is not None and stop_task not in done:
                    stop_task.cancel()
                try:
                    line = read_task.result()
                except asyncio.CancelledError:
                    return
                if not line:
                    return
                decoded = line.decode("utf-8", errors="replace")
                self.last_output_time = time.time()
                if callback is not None:
                    callback(decoded)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                self.log_path, "ERROR", f"fatal error reading {name} stream",
                error=str(exc), exception_type=type(exc).__name__,
            )
            raise
