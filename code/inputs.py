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
            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise InputError(f"Duplicate columns: {path}")
            missing = [field for field in REQUEST_FIELDS if field not in reader.fieldnames]
            if missing:
                raise InputError(f"Input is missing required columns: {', '.join(missing)}")
            for line_no, row in enumerate(reader, start=2):
                try:
                    if None in row or any(row.get(key) is None for key in REQUEST_FIELDS):
                        raise InputError(f"Malformed request at line {line_no}")
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
        from .evidence import timestamp
        return timestamp(value)
    except ValueError as exc:
        raise InputError(f"invalid {key} on line {line_no}: {value!r}") from exc


def _parse_optional_datetime(row: dict[str, str | None], key: str, line_no: int) -> datetime | None:
    value = row.get(key)
    if value is None or not value.strip():
        return None
    try:
        from .evidence import timestamp
        return timestamp(value.strip())
    except ValueError as exc:
        raise InputError(f"invalid {key} on line {line_no}: {value!r}") from exc



TABLE_FIELDS = {
    'user_identities': ('user_id', 'name', 'email', 'phone', 'email_hash', 'updated_at'),
    'user_audit_log': ('audit_id', 'user_id', 'event_time', 'field_name', 'old_value', 'new_value'),
    'system_activity': ('activity_id', 'event_time', 'event_type', 'source_system', 'target_system', 'resource_id', 'reported_result', 'details'),
    'deletion_rules': ('rule_id', 'data_category', 'condition', 'required_action'),
    'evidence_files': ('file_id', 'file_path', 'origin', 'captured_at'),
}


def load_tables(dataset: Path) -> dict[str, list[dict[str, str]]]:
    """Validate schemas, unique IDs, foreign keys, timestamps, and evidence paths."""
    from .evidence import timestamp
    tables = {}
    for name, fields in TABLE_FIELDS.items():
        path = dataset / f'{name}.csv'
        try:
            with path.open(encoding='utf-8-sig', newline='') as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or set(fields) - set(reader.fieldnames):
                    raise InputError(f'{name}: missing or duplicate columns')
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error) as exc:
            raise InputError(f'Cannot read {name}: {exc}') from exc
        seen = set()
        for index, row in enumerate(rows, 2):
            if None in row or any(row.get(key) is None for key in fields):
                raise InputError(f'{name}:{index}: malformed row')
            identifier = _required(row, fields[0])
            if identifier in seen:
                raise InputError(f'{name}:{index}: duplicate {fields[0]}')
            seen.add(identifier)
            required = {
                'user_identities': ('user_id',),
                'user_audit_log': ('user_id', 'field_name'),
                'system_activity': ('event_type', 'source_system', 'target_system', 'resource_id'),
                'deletion_rules': ('data_category', 'condition', 'required_action'),
                'evidence_files': ('file_path', 'origin'),
            }
            for key in required[name]:
                _required(row, key)
            for key in fields:
                if key.endswith('_at') or key == 'event_time':
                    try:
                        timestamp(_required(row, key))
                    except ValueError as exc:
                        raise InputError(f'{name}:{index}: invalid {key}') from exc
            if name == 'evidence_files':
                resolved = (dataset / row['file_path']).resolve()
                if not resolved.is_relative_to((dataset / 'evidence').resolve()) or not resolved.is_file():
                    raise InputError(f'{name}:{index}: missing or unsafe evidence path')
        tables[name] = rows
    users = {row['user_id'] for row in tables['user_identities']}
    if any(row['user_id'] not in users for row in tables['user_audit_log']):
        raise InputError('Audit history references a missing user_id')
    return tables
