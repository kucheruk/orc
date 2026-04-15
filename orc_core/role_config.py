#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .infra.io.atomic_io import write_json_atomic
from .config import DEFAULT_MODEL
from .infra.io.state_paths import role_settings_path

BASE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BASE_DIR / "prompts"
COMMIT_PROMPT_PATH = PROMPTS_DIR / "commit.txt"
MERGE_EXPERT_PROMPT_PATH = PROMPTS_DIR / "merge_expert.txt"

ROLE_CODER = "coder"
ROLE_HANDOFF = "handoff"
ROLE_MERGE_EXPERT = "merge_expert"

ALL_ROLE_IDS = (
    ROLE_CODER,
    ROLE_HANDOFF,
    ROLE_MERGE_EXPERT,
)

ROLE_SETTINGS_VISIBLE_IDS = (
    ROLE_CODER,
    ROLE_HANDOFF,
)


@dataclass(frozen=True)
class RoleDefinition:
    role_id: str
    title: str
    default_enabled: bool
    can_toggle_enabled: bool
    default_prompt_path: Optional[Path] = None
    default_prompt_text: str = ""


@dataclass(frozen=True)
class RoleResolvedConfig:
    role_id: str
    title: str
    enabled: bool
    can_toggle_enabled: bool
    model: str
    prompt: str


class RoleProfileRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, RoleDefinition] = {
            ROLE_CODER: RoleDefinition(
                role_id=ROLE_CODER,
                title="Кодер",
                default_enabled=True,
                can_toggle_enabled=True,
                default_prompt_text="(kanban mode — model config only)",
            ),
            ROLE_HANDOFF: RoleDefinition(
                role_id=ROLE_HANDOFF,
                title="Сдача кода",
                default_enabled=True,
                can_toggle_enabled=False,
                default_prompt_path=COMMIT_PROMPT_PATH,
            ),
            ROLE_MERGE_EXPERT: RoleDefinition(
                role_id=ROLE_MERGE_EXPERT,
                title="Merge Expert",
                default_enabled=False,
                can_toggle_enabled=False,
                default_prompt_path=MERGE_EXPERT_PROMPT_PATH,
            ),
        }

    def definitions(self) -> list[RoleDefinition]:
        return [self._definitions[role_id] for role_id in ALL_ROLE_IDS]

    def load_prompt(self, path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    def default_prompt(self, role_id: str) -> str:
        definition = self._require_definition(role_id)
        if definition.default_prompt_path is not None:
            return self.load_prompt(definition.default_prompt_path)
        return definition.default_prompt_text

    def load_overrides(self, workdir: str) -> dict[str, dict[str, object]]:
        path = role_settings_path(workdir)
        legacy_path = Path(workdir) / ".orc" / "role-settings.json"
        if not path.exists() and legacy_path.exists():
            path = legacy_path
        if not path.exists():
            return {}
        try:
            raw_payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Некорректный JSON в {path}.") from exc
        roles = raw_payload.get("roles") if isinstance(raw_payload, dict) else None
        if not isinstance(roles, dict):
            return {}
        parsed: dict[str, dict[str, object]] = {}
        for role_id in ALL_ROLE_IDS:
            raw_role = roles.get(role_id)
            if isinstance(raw_role, dict):
                parsed[role_id] = dict(raw_role)
        return parsed

    def save_overrides(self, workdir: str, overrides: dict[str, dict[str, object]]) -> None:
        path = role_settings_path(workdir)
        payload = {"version": 1, "roles": overrides}
        write_json_atomic(path, payload, ensure_ascii=False, indent=2)
        legacy_path = Path(workdir) / ".orc" / "role-settings.json"
        write_json_atomic(legacy_path, payload, ensure_ascii=False, indent=2)

    def update_override(
        self,
        workdir: str,
        role_id: str,
        *,
        enabled: Optional[bool] = None,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> None:
        definition = self._require_definition(role_id)
        overrides = self.load_overrides(workdir)
        role_override = dict(overrides.get(role_id, {}))
        if enabled is not None and definition.can_toggle_enabled:
            role_override["enabled"] = bool(enabled)
        if model is not None:
            trimmed_model = str(model).strip()
            if trimmed_model:
                role_override["model"] = trimmed_model
            else:
                role_override.pop("model", None)
        if prompt is not None:
            trimmed_prompt = str(prompt).strip()
            if trimmed_prompt:
                role_override["prompt"] = prompt
            else:
                role_override.pop("prompt", None)
        overrides[role_id] = role_override
        self.save_overrides(workdir, overrides)

    def resolve_role(
        self,
        workdir: str,
        role_id: str,
        *,
        cli_model: str = "",
        cli_prompt_path: str = "",
    ) -> RoleResolvedConfig:
        definition = self._require_definition(role_id)
        overrides = self.load_overrides(workdir)
        role_override = overrides.get(role_id, {})

        model = str(cli_model).strip()
        if not model:
            model = str(role_override.get("model") or "").strip() or DEFAULT_MODEL

        prompt_path = str(cli_prompt_path).strip()
        if prompt_path:
            prompt = self.load_prompt(Path(prompt_path))
        else:
            prompt_override = str(role_override.get("prompt") or "")
            prompt = prompt_override if prompt_override.strip() else self.default_prompt(role_id)

        enabled = definition.default_enabled
        if definition.can_toggle_enabled:
            raw_enabled = role_override.get("enabled")
            if isinstance(raw_enabled, bool):
                enabled = raw_enabled

        return RoleResolvedConfig(
            role_id=role_id,
            title=definition.title,
            enabled=enabled,
            can_toggle_enabled=definition.can_toggle_enabled,
            model=model,
            prompt=prompt,
        )

    def _require_definition(self, role_id: str) -> RoleDefinition:
        if role_id not in self._definitions:
            raise KeyError(f"Unknown role id: {role_id}")
        return self._definitions[role_id]
