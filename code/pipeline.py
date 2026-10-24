"""Request-first, cutoff-safe evidence retrieval; no model or prediction shortcuts."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from functools import lru_cache

from .evidence import Fact, make_fact, parse_file, timestamp
from .inputs import load_tables
from .models import DeletionRequest


@dataclass(frozen=True)
class Intent:
    decision: str
    reason: str


def classify_request(text: str) -> Intent:
    """Conservatively recognize explicit deletion and explicit non-deletion intent."""
    text = text.casefold().replace('’', "'")
    negative = r"(?:do not|don't|not a request to|not asking for)\s+(?:delete|erase|close|deletion)|without removing|marketing lists only|stop the promotional|continue using|resetting the login|copy of|portable format|correct|out of date|information request"
    if re.search(r'marketing lists only|stop the promotional|without removing any|not asking for deletion|not a request to erase|do not close|don.t delete or change', text):
        return Intent('NOT_APPLICABLE', 'Explicit non-deletion restriction')
    positive = r'delet|eras|remov|clos.{0,20}account|account.{0,30}clos|confirm.{0,50}profile is gone|suppr|elimin|exclusão|削除|삭제'
    # Remove explicit prohibition clauses before searching for affirmative intent.
    cleaned = re.sub(r"(?:do not|don't|not a request to|not asking for)\s+(?:delete|erase|close|deletion)[^.]*", '', text)
    if re.search(negative, text) and not re.search(positive, re.sub(negative, '', cleaned)):
        return Intent('NOT_APPLICABLE', 'Explicit non-deletion request')
    if re.search(positive, cleaned):
        return Intent('AUTHORIZED', 'Deletion or deletion-verification language')
    return Intent('UNCERTAIN', 'No unambiguous supported deletion intent; review required')


@dataclass(frozen=True)
class IdentityLink:
    user_id: str
    field: str
    value: str
    evidence_id: str
    observed_at: str
    confidence: str


def resolve_identity(request: DeletionRequest, tables: dict) -> tuple[list[IdentityLink], list[str]]:
    """Use only snapshots and history available by cutoff; keep ambiguous users separate."""
    cutoff = request.audit_at
    snapshots = [row for row in tables['user_identities'] if timestamp(row['updated_at']) <= cutoff]
    history = [row for row in tables['user_audit_log'] if timestamp(row['event_time']) <= cutoff]
    email = request.email.casefold()
    users = {row['user_id'] for row in snapshots if row['email'].casefold() == email}
    users.update(row['user_id'] for row in history if row['field_name'] == 'email' and email in (row['old_value'].casefold(), row['new_value'].casefold()))
    if len(users) != 1:
        return [], ['identity_not_found' if not users else 'ambiguous_identity']
    user = next(iter(users))
    links = []
    for row in snapshots:
        if row['user_id'] == user:
            for key in ('user_id', 'name', 'email', 'phone', 'email_hash'):
                if row[key]:
                    links.append(IdentityLink(user, key, row[key], f'user_identities:{user}', row['updated_at'], 'exact_snapshot'))
    for row in history:
        if row['user_id'] == user:
            links.append(IdentityLink(user, 'user_id', user, row['audit_id'], row['event_time'], 'exact_history'))
            for key in ('old_value', 'new_value'):
                if row[key]:
                    links.append(IdentityLink(user, row['field_name'], row[key], row['audit_id'], row['event_time'], 'exact_history'))
    return links, []


@lru_cache(maxsize=2048)
def identifier_pattern(identifiers: tuple[str, ...]) -> re.Pattern:
    """Cache one boundary-aware search expression per identifier set."""
    alternatives = '|'.join(re.escape(value) for value in identifiers) or r'(?!)'
    return re.compile(r'(?<![\w@.+-])(?:' + alternatives + r')(?![\w@.+-])')


def matches(text: str, identifiers: set[str]) -> bool:
    """Match complete identifiers, never user_1 inside user_10 or email substrings."""
    values = tuple(sorted({value.casefold() for value in identifiers if value}))
    return bool(identifier_pattern(values).search(text.casefold()))


def before_cutoff(fact: Fact, request: DeletionRequest) -> bool:
    """Require manifest availability and every explicit event time to precede audit."""
    return all(timestamp(value) <= request.audit_at for value in (fact.captured_at, *fact.event_times))


@dataclass
class CasePacket:
    case_id: str
    audit_at: str
    intent: Intent
    deletion_status: str | None = None
    steps_json: list = field(default_factory=list)
    identity_links: list[IdentityLink] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    rules: list[dict] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)
    omitted_facts: int = 0

    def to_json(self) -> str:
        """Serialize deterministically for inspection or later model integration."""
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, indent=2)


class EvidencePipeline:
    def __init__(self, dataset: Path, max_facts: int = 150, max_chars: int = 60000):
        """Load participant tables; parse artifacts lazily after intent authorization."""
        if max_facts < 1 or max_chars < 1:
            raise ValueError('Packet limits must be positive')
        self.dataset = dataset.resolve()
        self.tables = load_tables(self.dataset)
        self.max_facts = max_facts
        self.max_chars = max_chars
        self.cache: dict[str, list[Fact]] = {}

    def packet(self, request: DeletionRequest) -> CasePacket:
        """Build grounded closure over resource IDs, keeping claims labeled and bounded."""
        intent = classify_request(request.request_text)
        packet = CasePacket(request.case_id, request.audit_at.isoformat(), intent)
        if intent.decision == 'NOT_APPLICABLE':
            packet.deletion_status = 'NOT_APPLICABLE'
            return packet
        if intent.decision != 'AUTHORIZED':
            packet.uncertainty.append('intent_requires_review')
            return packet
        packet.identity_links, packet.uncertainty = resolve_identity(request, self.tables)
        if not packet.identity_links:
            return packet
        packet.rules = self.tables['deletion_rules']
        identifiers = {link.value for link in packet.identity_links if link.field != 'name'}
        names = {link.value for link in packet.identity_links if link.field == 'name'}
        candidates = []
        for source in self.tables['evidence_files']:
            if timestamp(source['captured_at']) > request.audit_at:
                continue
            try:
                if source['file_id'] not in self.cache:
                    self.cache[source['file_id']] = parse_file(source, self.dataset)
                candidates.extend(fact for fact in self.cache[source['file_id']] if before_cutoff(fact, request))
            except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
                packet.uncertainty.append(f"{source['file_id']}: extraction unavailable ({type(exc).__name__})")
        for row in self.tables['system_activity']:
            if timestamp(row['event_time']) <= request.audit_at:
                source = {'file_id': row['activity_id'], 'captured_at': row['event_time']}
                candidates.append(make_fact(source, 'system_activity.csv', json.dumps(row, sort_keys=True), row['target_system'], 'claim'))
        selected = []
        pending = candidates
        while pending:
            remaining = []
            found = False
            for fact in pending:
                if matches(fact.text, identifiers):
                    selected.append(fact)
                    identifiers.update(fact.resource_ids)
                    found = True
                else:
                    remaining.append(fact)
            if not found:
                break
            pending = remaining
        for fact in pending:
            if matches(fact.text, names):
                selected.append(replace(fact, uncertainty=(*fact.uncertainty, 'name_only_match_requires_review')))
        selected.sort(key=lambda f: (f.captured_at, f.evidence_id, f.location))
        used = 0
        for fact in selected:
            size = len(json.dumps(asdict(fact), ensure_ascii=False))
            if len(packet.facts) >= self.max_facts or used + size > self.max_chars:
                packet.omitted_facts += 1
                continue
            packet.facts.append(fact)
            used += size
        if packet.omitted_facts:
            packet.uncertainty.append('packet_truncated_requires_followup')
        if not packet.facts:
            packet.uncertainty.append('no_grounded_evidence')
        return packet
