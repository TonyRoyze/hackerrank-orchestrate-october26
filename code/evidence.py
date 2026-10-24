"""Record-level extraction with attributable locations; never executes supplied SQL."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})')
RESOURCE = re.compile(r'\b(?:account|analytics|audit_record|backup|data_flow|export|search|support|identifier)_[0-9]+\b')


def timestamp(value: str) -> datetime:
    """Normalize ISO timestamps; reject ambiguous timezone-free inputs."""
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp requires a timezone')
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class Fact:
    evidence_id: str
    location: str
    captured_at: str
    event_times: tuple[str, ...]
    system_id: str
    resource_ids: tuple[str, ...]
    kind: str
    text: str
    uncertainty: tuple[str, ...] = ()


def make_fact(source: dict, location: str, text: str, system: str = '', kind: str = 'observation', times: tuple = (), uncertainty: tuple = ()) -> Fact:
    """Attach manifest availability and all explicit record timestamps."""
    return Fact(source['file_id'], location, source['captured_at'],
                tuple(sorted(set(times) | set(STAMP.findall(text)))), system,
                tuple(sorted(set(RESOURCE.findall(text)))), kind, text, uncertainty)


def json_facts(value: object, source: dict, location: str = '$', context: dict | None = None) -> list[Fact]:
    """Split nested bundles at resource records, inheriting snapshot context only."""
    context = dict(context or {})
    facts = []
    if isinstance(value, dict):
        for key in ('captured_at', 'exported_at', 'snapshot_at', 'data_store', 'origin_system', 'system_id', 'collection'):
            if key in value and not isinstance(value[key], (dict, list)):
                context[key] = value[key]
        if 'resource_id' in value:
            text = json.dumps({'context': context, 'record': value}, ensure_ascii=False, sort_keys=True)
            return [make_fact(source, location, text, str(context.get('data_store', context.get('origin_system', context.get('system_id', '')))))]
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                facts.extend(json_facts(child, source, f'{location}.{key}', context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            facts.extend(json_facts(child, source, f'{location}[{index}]', context))
    return facts


def sql_values(text: str) -> list[str | None]:
    """Read SQLite literal tuples without running statements or loading extensions."""
    tokens = re.findall(r"'(?:''|[^'])*'|NULL|-?\d+(?:\.\d+)?", text)
    return [None if token == 'NULL' else token[1:-1].replace("''", "'") if token.startswith("'") else token for token in tokens]


def parse_file(source: dict, dataset: Path) -> list[Fact]:
    """Extract JSON, SQL rows, trace-linked logs, text, PDF pages, or OCR lines."""
    path = (dataset / source['file_path']).resolve()
    if not path.is_relative_to((dataset / 'evidence').resolve()):
        raise ValueError('Evidence path escapes dataset/evidence')
    suffix = path.suffix.lower()
    if suffix in ('.pdf', '.png', '.jpg', '.jpeg'):
        program = 'pdftotext' if suffix == '.pdf' else 'tesseract'
        if not shutil.which(program):
            raise ValueError(f'{program} is required for {suffix} evidence')
        command = [program, '-layout', str(path), '-'] if suffix == '.pdf' else [program, str(path), 'stdout']
        text = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60).stdout
        if not text.strip():
            raise ValueError('No extractable document text; OCR or visual review required')
        # A page can contain multiple subjects: line-level units avoid bulk attribution.
        return [make_fact(source, f'line:{i}', line, uncertainty=('extracted_text_requires_review',)) for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    text = path.read_text(encoding='utf-8-sig')
    if suffix == '.json':
        return json_facts(json.loads(text), source)
    facts = []
    traces: dict[str, list[tuple[int, str]]] = {}
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if suffix == '.sql':
            match = re.match(r'INSERT INTO ["\[]?(\w+)["\]]?\s+VALUES\((.*)\);', line)
            if not match:
                continue
            values = sql_values(match[2])
            facts.append(make_fact(source, f'{match[1]}:line:{i}', json.dumps({'table': match[1], 'values': values}, ensure_ascii=False), str(values[1] or '') if len(values) > 1 else ''))
        elif suffix == '.log':
            trace = re.search(r'\btrace_id=(\S+)', line)
            if trace:
                traces.setdefault(trace[1], []).append((i, line))
            else:
                facts.append(make_fact(source, f'line:{i}', line, kind='claim'))
        else:
            parts = line.split('|')
            facts.append(make_fact(source, f'line:{i}', line, parts[1].strip() if len(parts) > 2 else ''))
    for trace, lines in traces.items():
        joined = '\n'.join(line for _, line in lines)
        service = re.search(r'\bservice=(\S+)', joined)
        # Logs remain claims: reads/scans do not establish all required final state.
        facts.append(make_fact(source, f'trace:{trace}', joined, service[1] if service else '', 'claim'))
    return facts
