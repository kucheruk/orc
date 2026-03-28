#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI-powered conflict analysis and task distribution across parallel queues."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .logging import log_event
from .task_source import Task

if TYPE_CHECKING:
    from .backend import Backend

GIT_LS_TIMEOUT_SECONDS = 10.0
AGENT_ANALYSIS_TIMEOUT_SECONDS = 120.0
TASK_TEXT_MAX_LENGTH = 200
PROJECT_STRUCTURE_MAX_LINES = 200
PROJECT_STRUCTURE_MAX_DEPTH = 3
NO_CONFLICTS_MARKER = "NO_CONFLICTS"
CONFLICT_PATTERN = re.compile(r"CONFLICT:\s*(\S+)\s*<->\s*(\S+)\s*\|\s*(.+)")


@dataclass(frozen=True)
class ConflictEdge:
    task_a: str
    task_b: str
    reason: str


@dataclass
class TaskDistribution:
    queues: dict[int, list[str]]
    conflicts: list[ConflictEdge]
    analysis_text: str


class TaskAnalyzer:
    """Calls LLM to predict which tasks conflict, then distributes to queues."""

    def __init__(self, *, workdir: str, model: str, log_path: Path, backend: Optional["Backend"] = None) -> None:
        self.workdir = workdir
        self.model = model
        self.log_path = log_path
        self._backend = backend

    def analyze(self, tasks: list[Task], num_queues: int) -> TaskDistribution:
        if len(tasks) <= 1 or num_queues <= 1:
            return TaskDistribution(
                queues={0: [t.task_id for t in tasks]}, conflicts=[], analysis_text="")

        task_ids = [t.task_id for t in tasks]
        log_event(self.log_path, "INFO", "conflict analysis starting",
                  task_count=len(tasks), num_queues=num_queues)

        llm_output = self._call_agent(self._build_prompt(tasks))
        conflicts = parse_conflicts(llm_output, set(task_ids))
        queues = distribute_to_queues(task_ids, conflicts, num_queues)

        log_event(self.log_path, "INFO", "conflict analysis completed",
                  conflicts_found=len(conflicts),
                  queue_sizes={k: len(v) for k, v in queues.items()})

        return TaskDistribution(queues=queues, conflicts=conflicts, analysis_text=llm_output)

    def _build_prompt(self, tasks: list[Task]) -> str:
        template_path = Path(__file__).parent.parent / "prompts" / "conflict_analysis.txt"
        template = template_path.read_text(encoding="utf-8")
        return template.format(
            project_structure=_get_project_structure(self.workdir),
            tasks_list="\n".join(f"- {t.task_id}: {t.text[:TASK_TEXT_MAX_LENGTH]}" for t in tasks),
            task_id_a="{task_id_a}",
            task_id_b="{task_id_b}",
        )

    def _build_text_cmd(self, prompt: str) -> list[str]:
        if self._backend is None:
            from .backend import get_backend
            self._backend = get_backend()
        name = self._backend.name
        if name == "cursor":
            return ["agent", "-p", "--force", "--model", self.model, "--output-format", "text", prompt]
        if name == "claude":
            return ["claude", "-p", "--model", self.model, "--dangerously-skip-permissions", prompt]
        if name == "codex":
            return ["codex", "exec", "--full-auto", "--model", self.model, prompt]
        return ["agent", "-p", "--force", "--model", self.model, "--output-format", "text", prompt]

    def _call_agent(self, prompt: str) -> str:
        cmd = self._build_text_cmd(prompt)
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workdir, capture_output=True, text=True,
                timeout=AGENT_ANALYSIS_TIMEOUT_SECONDS,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log_event(self.log_path, "WARN", "conflict analysis failed", error=str(exc))
            return ""
        return result.stdout or ""


# ── Parsing ──────────────────────────────────────────────────────

def parse_conflicts(llm_output: str, valid_ids: set[str]) -> list[ConflictEdge]:
    edges: list[ConflictEdge] = []
    for line in llm_output.splitlines():
        stripped = line.strip()
        if stripped == NO_CONFLICTS_MARKER:
            return []
        match = CONFLICT_PATTERN.match(stripped)
        if match:
            a, b, reason = match.group(1), match.group(2), match.group(3).strip()
            if a in valid_ids and b in valid_ids and a != b:
                edges.append(ConflictEdge(task_a=a, task_b=b, reason=reason))
    return edges


# ── Distribution ─────────────────────────────────────────────────

def distribute_to_queues(
    task_ids: list[str],
    conflicts: list[ConflictEdge],
    num_queues: int,
) -> dict[int, list[str]]:
    if not task_ids:
        return {i: [] for i in range(num_queues)}
    graph = _build_conflict_graph(task_ids, conflicts)
    components = _find_connected_components(task_ids, graph)
    return _assign_components_to_queues(components, num_queues)


def _build_conflict_graph(task_ids: list[str], conflicts: list[ConflictEdge]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {task_id: set() for task_id in task_ids}
    for edge in conflicts:
        if edge.task_a in adjacency and edge.task_b in adjacency:
            adjacency[edge.task_a].add(edge.task_b)
            adjacency[edge.task_b].add(edge.task_a)
    return adjacency


def _find_connected_components(task_ids: list[str], adjacency: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    components: list[list[str]] = []
    for task_id in task_ids:
        if task_id in visited:
            continue
        component: list[str] = []
        stack = [task_id]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            stack.extend(adjacency[node] - visited)
        components.append(component)
    return components


def _assign_components_to_queues(components: list[list[str]], num_queues: int) -> dict[int, list[str]]:
    components.sort(key=len, reverse=True)
    queues: dict[int, list[str]] = {i: [] for i in range(num_queues)}
    for component in components:
        lightest_queue = min(range(num_queues), key=lambda q: len(queues[q]))
        queues[lightest_queue].extend(component)
    return queues


# ── Project structure ────────────────────────────────────────────

def _get_project_structure(workdir: str) -> str:
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"],
            cwd=workdir, capture_output=True, text=True,
            timeout=GIT_LS_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return "(structure unavailable)"
    if result.returncode != 0:
        return "(structure unavailable)"

    files = result.stdout.strip().splitlines()
    dirs: set[str] = set()
    for filepath in files:
        parts = filepath.split("/")
        for depth in range(1, min(len(parts), PROJECT_STRUCTURE_MAX_DEPTH + 1)):
            dirs.add("/".join(parts[:depth]) + "/")
    top_level_files = [f for f in files if "/" not in f]
    return "\n".join((sorted(dirs) + top_level_files)[:PROJECT_STRUCTURE_MAX_LINES])
