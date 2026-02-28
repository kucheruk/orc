#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import threading
from pathlib import Path
from typing import Optional

from prompt_toolkit.shortcuts import radiolist_dialog

DEFAULT_MODEL = "gpt-5.3-codex"
MODEL_STATE_PATH = Path(".orc") / "model-selection.json"


class ModelSelectionError(RuntimeError):
    pass


class ModelListLoader:
    def __init__(self) -> None:
        self._done = threading.Event()
        self._models: Optional[list[str]] = None
        self._error: Optional[BaseException] = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._models = list_supported_models()
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


def list_supported_models() -> list[str]:
    try:
        result = subprocess.run(
            ["agent", "--list-models"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ModelSelectionError("Команда agent недоступна для получения списка моделей.") from exc
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise ModelSelectionError(f"Не удалось выполнить `agent --list-models`: {stderr or 'unknown error'}")
    models: list[str] = []
    for raw in (result.stdout or "").splitlines():
        model = raw.strip()
        if model and model not in models:
            models.append(model)
    if not models:
        raise ModelSelectionError("Список моделей пуст. Проверьте `agent --list-models`.")
    return models


def start_model_list_loading() -> ModelListLoader:
    return ModelListLoader()


def load_last_selected_model(workdir: str) -> Optional[str]:
    path = Path(workdir) / MODEL_STATE_PATH
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelSelectionError(f"Некорректный JSON в {path}.") from exc
    model = str(payload.get("last_selected_model") or "").strip()
    return model or None


def save_last_selected_model(workdir: str, model: str) -> None:
    path = Path(workdir) / MODEL_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_selected_model": model}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def choose_model_interactive(models: list[str], default_model: str) -> str:
    if not models:
        raise ModelSelectionError("Невозможно показать выбор модели: список моделей пуст.")
    selected_default = default_model if default_model in models else models[0]
    values: list[tuple[str, str]] = []
    for model in models:
        label = f"{model} (default)" if model == selected_default else model
        values.append((model, label))
    selected = radiolist_dialog(
        title="Выбор модели",
        text="Выберите модель для запуска задач ORC",
        values=values,
        default=selected_default,
    ).run()
    if selected is None:
        raise KeyboardInterrupt
    return selected
