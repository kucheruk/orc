#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter for incident.ports.ArtifactWriter — atomic text writes."""
from __future__ import annotations

from pathlib import Path

from .atomic_io import write_text_atomic


class FsArtifactWriter:
    """Writes text artifacts atomically to the filesystem."""

    def write_text(self, path: Path, text: str) -> None:
        write_text_atomic(path, text)


DEFAULT_ARTIFACT_WRITER = FsArtifactWriter()
