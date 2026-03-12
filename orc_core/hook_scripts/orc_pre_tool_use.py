#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import Any

import orc_hook_lib as lib

WRITE_TOOL_NAMES = {
    "ApplyPatch",
    "Delete",
    "Edit",
    "EditNotebook",
    "MultiEdit",
    "NotebookEdit",
    "Write",
}
RESTRICTED_STAGES = {"planning", "review"}


def _task_file_path(script_repo: Path) -> Path:
    env_task_file = str(os.environ.get("ORC_TASK_FILE") or "").strip()
    return Path(env_task_file) if env_task_file else (script_repo / ".cursor" / "orc-task.json")


def _base_workspace(script_repo: Path) -> Path:
    return Path(str(os.environ.get("ORC_BASE_WORKSPACE") or "").strip() or str(script_repo))


def _read_stage_id(task_file: Path) -> str:
    payload = lib.read_json(task_file, {})
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("sdlc_stage_id") or "").strip().lower()


def _extract_paths_from_mapping(payload: dict[str, Any]) -> list[str]:
    candidates = [
        payload.get("path"),
        payload.get("file_path"),
        payload.get("target_file"),
        payload.get("target_notebook"),
        payload.get("filepath"),
    ]
    return [str(value).strip() for value in candidates if str(value or "").strip()]


def _extract_paths(tool_name: str, tool_input: Any) -> tuple[list[str], bool]:
    if tool_name == "Shell":
        command = str((tool_input or {}).get("command") if isinstance(tool_input, dict) else "").strip()
        is_write_shell = ">" in command or ">>" in command or " tee " in f" {command} "
        return [], is_write_shell

    if not isinstance(tool_input, dict):
        if tool_name in WRITE_TOOL_NAMES:
            return [], True
        return [], False

    paths = _extract_paths_from_mapping(tool_input)
    if tool_name == "ApplyPatch":
        patch_text = tool_input.get("input") or tool_input.get("patch") or ""
        paths.extend(lib.extract_applypatch_paths(patch_text))
    if tool_name in WRITE_TOOL_NAMES:
        return paths, True
    return paths, bool(paths)


def _deny(reason: str) -> int:
    sys.stdout.write(json.dumps({"decision": "deny", "reason": reason}))
    sys.stdout.flush()
    return 0


def _allow() -> int:
    sys.stdout.write(json.dumps({"decision": "allow"}))
    sys.stdout.flush()
    return 0


def main() -> int:
    script_repo = Path(__file__).resolve().parents[2]
    base_workspace = _base_workspace(script_repo)
    log_path = base_workspace / ".orc" / "orc-hook.log"
    try:
        raw = sys.stdin.read() or "{}"
        data = json.loads(raw)
    except Exception as exc:
        lib.log_event(log_path, "ERROR", "preToolUse: bad input", error=str(exc))
        return _allow()

    roots = data.get("workspace_roots") or []
    normalized_roots = {str(lib.normalize_path(root)) for root in roots}
    allowed_roots = {str(lib.normalize_path(script_repo)), str(lib.normalize_path(base_workspace))}
    if normalized_roots and not normalized_roots.intersection(allowed_roots):
        return _allow()

    task_file = _task_file_path(script_repo)
    stage_id = _read_stage_id(task_file)
    if stage_id not in RESTRICTED_STAGES:
        return _allow()

    tool_name = str(data.get("tool_name") or "").strip()
    tool_input = data.get("tool_input")
    cwd = str(data.get("cwd") or "").strip()
    paths, is_write_attempt = _extract_paths(tool_name, tool_input)
    if not is_write_attempt:
        return _allow()

    if not paths:
        return _deny(f"SDLC stage `{stage_id}`: write tools are limited to .orc/artifacts only.")
    for raw_path in paths:
        if not lib.is_artifact_path(raw_path, base_workspace, cwd):
            return _deny(f"SDLC stage `{stage_id}`: write is allowed only in .orc/artifacts.")
    return _allow()


if __name__ == "__main__":
    raise SystemExit(main())
