#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path


def _run_from_orc_project() -> int:
    project_root = Path(__file__).resolve().parent
    cmd = [
        "uv",
        "run",
        "--project",
        str(project_root),
        "python",
        str(Path(__file__).resolve()),
        *sys.argv[1:],
    ]
    env = os.environ.copy()
    env["ORC_BOOTSTRAPPED"] = "1"
    try:
        return subprocess.call(cmd, env=env)
    except KeyboardInterrupt:
        # Keep Ctrl+C UX clean when bootstrap child is running.
        return 130


def _extract_dependency_name(spec: str) -> str | None:
    base = spec.split(";", 1)[0].strip()
    if not base:
        return None
    if "[" in base:
        base = base.split("[", 1)[0]
    match = re.match(r"^[A-Za-z0-9_.-]+", base)
    if not match:
        return None
    return match.group(0).lower()


def _runtime_dependency_modules(project_root: Path) -> set[str]:
    pyproject_path = project_root / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    dependencies = data.get("project", {}).get("dependencies", [])
    modules: set[str] = set()
    for dependency_spec in dependencies:
        if not isinstance(dependency_spec, str):
            continue
        package_name = _extract_dependency_name(dependency_spec)
        if package_name:
            modules.add(package_name.replace("-", "_"))
    return modules


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    runtime_deps = _runtime_dependency_modules(project_root)
    try:
        from orc_core.cli_app import main
    except ModuleNotFoundError as exc:
        if exc.name in runtime_deps and os.environ.get("ORC_BOOTSTRAPPED") != "1":
            raise SystemExit(_run_from_orc_project())
        raise
    raise SystemExit(main())
