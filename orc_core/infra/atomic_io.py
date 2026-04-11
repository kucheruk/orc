#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _fsync_directory(path: Path) -> None:
    try:
        dir_fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        return
    finally:
        os.close(dir_fd)


def write_text_atomic(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        _fsync_directory(path.parent)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def write_json_atomic(path: Path, payload: dict[str, Any], ensure_ascii: bool = False, indent: int = 2) -> None:
    write_text_atomic(path, json.dumps(payload, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8")
