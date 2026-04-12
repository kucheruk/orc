#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..infra.io.atomic_io import write_json_atomic
from ..infra.state.state_paths import model_selection_path

if TYPE_CHECKING:
    from ..infra.backend import Backend

DEFAULT_MODEL = "gpt-5.3-codex"
AGENT_LIST_MODELS_TIMEOUT_SECONDS = 15.0


class ModelSelectionError(RuntimeError):
    pass


_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ModelListLoader:
    def __init__(self, backend: Optional["Backend"] = None) -> None:
        self._done = threading.Event()
        self._models: Optional[list[str]] = None
        self._error: Optional[BaseException] = None
        self._backend = backend
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._models = list_supported_models(backend=self._backend)
        except BaseException as exc:
            self._error = exc
        finally:
            self._done.set()

    def result(self, timeout: Optional[float] = None) -> list[str]:
        if not self._done.wait(timeout=timeout):
            raise ModelSelectionError("Не удалось получить список моделей: timeout.")
        if self._error is not None:
            raise ModelSelectionError(str(self._error)) from self._error
        if self._models is None:
            raise ModelSelectionError("Не удалось получить список моделей: пустой результат.")
        return self._models


def list_supported_models(backend: Optional["Backend"] = None) -> list[str]:
    if backend is None:
        from ..infra.backend import get_backend
        backend = get_backend()
    cmd = backend.list_models_cmd()
    if cmd is None:
        return [backend.default_model()]
    cmd_str = " ".join(cmd)
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env={**os.environ, "TERM": "dumb", "NO_COLOR": "1"},
            timeout=AGENT_LIST_MODELS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise ModelSelectionError(f"Команда {cmd[0]!r} недоступна для получения списка моделей.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ModelSelectionError(f"Не удалось выполнить `{cmd_str}`: timeout.") from exc
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise ModelSelectionError(f"Не удалось выполнить `{cmd_str}`: {stderr or 'unknown error'}")
    models: list[str] = []
    for raw in (result.stdout or "").splitlines():
        parsed_model = _parse_model_id(raw)
        if parsed_model and parsed_model not in models:
            models.append(parsed_model)
    if not models:
        raise ModelSelectionError("Список моделей пуст. Проверьте `agent --list-models`.")
    return models


def _parse_model_id(raw: str) -> Optional[str]:
    cleaned = _ANSI_ESCAPE_RE.sub("", raw or "").strip()
    if not cleaned:
        return None
    model_id = cleaned.split(" - ", 1)[0].strip()
    if not _MODEL_ID_RE.match(model_id):
        return None
    return model_id


def start_model_list_loading(backend: Optional["Backend"] = None) -> ModelListLoader:
    return ModelListLoader(backend=backend)


def load_last_selected_model(workdir: str) -> Optional[str]:
    path = model_selection_path(workdir)
    legacy_path = Path(workdir) / ".orc" / "model-selection.json"
    if not path.exists() and legacy_path.exists():
        path = legacy_path
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelSelectionError(f"Некорректный JSON в {path}.") from exc
    model = str(payload.get("last_selected_model") or "").strip()
    return model or None


def save_last_selected_model(workdir: str, model: str) -> None:
    path = model_selection_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_selected_model": model}
    write_json_atomic(path, payload, ensure_ascii=False, indent=2)
    legacy_path = Path(workdir) / ".orc" / "model-selection.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(legacy_path, payload, ensure_ascii=False, indent=2)


def choose_model_interactive(models: list[str], default_model: str) -> str:
    if not models:
        raise ModelSelectionError("Невозможно показать выбор модели: список моделей пуст.")
    return default_model if default_model in models else models[0]
