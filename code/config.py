"""Runtime settings; secrets are read from environment and never printed."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    repo_root: Path = REPO_ROOT
    dataset_dir: Path = REPO_ROOT / "dataset"
    output_path: Path = REPO_ROOT / "output.csv"
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        """Load model configuration without exposing credential values."""
        provider = os.getenv("AUDIT_MODEL_PROVIDER") or None
        model = os.getenv("AUDIT_MODEL_NAME") or None
        api_key = os.getenv("AUDIT_API_KEY") or None
        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            input_usd_per_million=_optional_float("AUDIT_INPUT_USD_PER_MILLION"),
            output_usd_per_million=_optional_float("AUDIT_OUTPUT_USD_PER_MILLION"),
        )

    def require_model_config(self) -> None:
        missing = []
        if not self.provider:
            missing.append("AUDIT_MODEL_PROVIDER")
        if not self.model:
            missing.append("AUDIT_MODEL_NAME")
        if not self.api_key:
            missing.append("AUDIT_API_KEY")
        if missing:
            raise ValueError("Model configuration is incomplete; set: " + ", ".join(missing))


def _optional_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{name} cannot be negative")
    return parsed

