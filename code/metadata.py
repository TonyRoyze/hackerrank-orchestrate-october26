"""Run metadata helpers for later evaluation and usage reporting."""

from __future__ import annotations

from datetime import datetime

from .models import RunMetadata


def finish_run(metadata: RunMetadata) -> RunMetadata:
    metadata.finished_at = datetime.now(metadata.started_at.tzinfo)
    return metadata

