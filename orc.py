#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
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
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    try:
        from orc_core.cli_app import main
    except ModuleNotFoundError as exc:
        runtime_deps = {"rich", "prompt_toolkit"}
        if exc.name in runtime_deps and os.environ.get("ORC_BOOTSTRAPPED") != "1":
            raise SystemExit(_run_from_orc_project())
        raise
    raise SystemExit(main())
