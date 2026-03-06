#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_ARTIFACT_SUFFIX_BY_STAGE_ID = {
    "planning": "plan",
    "design": "design",
    "implementation": "implementation",
    "review": "review",
    "testing": "testing",
    "handoff": "handoff",
}


def _safe_task_id(task_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(task_id or "").strip())
    return normalized or "TASK"


def _artifact_suffix_for_stage(stage_id: str) -> str:
    normalized = str(stage_id or "").strip().lower()
    if normalized in _ARTIFACT_SUFFIX_BY_STAGE_ID:
        return _ARTIFACT_SUFFIX_BY_STAGE_ID[normalized]
    fallback = re.sub(r"[^A-Za-z0-9_.-]+", "_", normalized)
    return fallback or "stage"


@dataclass(frozen=True)
class StageArtifactBundle:
    artifacts_dir: Path
    task_id: str
    plan: Path
    design: Path
    implementation: Path
    review: Path
    testing: Path
    handoff: Path

    def to_prompt_vars(self) -> Mapping[str, str]:
        return {
            "artifacts_dir": str(self.artifacts_dir),
            "artifact_plan": str(self.plan),
            "artifact_design": str(self.design),
            "artifact_implementation": str(self.implementation),
            "artifact_review": str(self.review),
            "artifact_testing": str(self.testing),
            "artifact_handoff": str(self.handoff),
        }

    def expected_for_stage(self, stage_id: str) -> Path:
        suffix = _artifact_suffix_for_stage(stage_id)
        return self.artifacts_dir / f"{_safe_task_id(self.task_id)}_{suffix}.md"


def build_stage_artifact_bundle(*, workdir: str, task_id: str) -> StageArtifactBundle:
    artifacts_dir = Path(workdir) / ".orc" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    safe_task_id = _safe_task_id(task_id)
    return StageArtifactBundle(
        artifacts_dir=artifacts_dir,
        task_id=safe_task_id,
        plan=artifacts_dir / f"{safe_task_id}_plan.md",
        design=artifacts_dir / f"{safe_task_id}_design.md",
        implementation=artifacts_dir / f"{safe_task_id}_implementation.md",
        review=artifacts_dir / f"{safe_task_id}_review.md",
        testing=artifacts_dir / f"{safe_task_id}_testing.md",
        handoff=artifacts_dir / f"{safe_task_id}_handoff.md",
    )


def validate_stage_artifact_output(*, stage_id: str, bundle: StageArtifactBundle) -> tuple[bool, str, Path]:
    artifact_path = bundle.expected_for_stage(stage_id)
    if not artifact_path.exists():
        return False, "missing", artifact_path
    try:
        body = artifact_path.read_text(encoding="utf-8").strip()
    except Exception:
        return False, "unreadable", artifact_path
    if not body:
        return False, "empty", artifact_path
    return True, "ok", artifact_path
