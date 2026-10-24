"""CSV input loading and basic structural validation."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import DeletionRequest


REQUEST_FIELDS = (
    "case_id",
    "email",
    "requested_at",
    "reported_status",
    "reported_at",
    "audit_at",
    "request_text",
)


class InputError(ValueError):
    """Raised when a participant-facing input file is invalid."""


def load_requests(path: Path) -> list[DeletionRequest]:
    if not path.is_file():
        raise InputError(f"Required input file not found: {path}")
    requests: list[DeletionRequest] = []
    seen: set[str] = set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise InputError(f"Input has no header: {path}")
            missing = [field for field in REQUEST_FIELDS if field not in reader.fieldnames]
            if missing:
                raise InputError(f"Input is missing required columns: {', '.join(missing)}")
            for line_no, row in enumerate(reader, start=2):
                try:
                    case_id = _required(row, "case_id")
                    if case_id in seen:
                        raise InputError(f"Duplicate case_id {case_id!r} at line {line_no}")
                    seen.add(case_id)
                    requests.append(
                        DeletionRequest(
                            case_id=case_id,
                            email=_required(row, "email"),
                            requested_at=_parse_datetime(row, "requested_at", line_no),
                            reported_status=_required(row, "reported_status"),
                            reported_at=_parse_optional_datetime(row, "reported_at", line_no),
                            audit_at=_parse_datetime(row, "audit_at", line_no),
                            request_text=_required(row, "request_text"),
                        )
                    )
                except (ValueError, TypeError) as exc:
                    if isinstance(exc, InputError):
                        raise
                    raise InputError(f"Invalid request at line {line_no}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InputError(f"Input is not valid UTF-8: {path}") from exc
    return requests


def _required(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None or not value.strip():
        raise InputError(f"{key} is blank")
    return value.strip()


def _parse_datetime(row: dict[str, str | None], key: str, line_no: int) -> datetime:
    value = _required(row, key)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"invalid {key} on line {line_no}: {value!r}") from exc


def _parse_optional_datetime(row: dict[str, str | None], key: str, line_no: int) -> datetime | None:
    value = row.get(key)
    if value is None or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"invalid {key} on line {line_no}: {value!r}") from exc

