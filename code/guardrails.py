"""Strict reasoning-input validation; model text never grants capabilities."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .evidence import timestamp
from .pipeline import CasePacket

OPERATIONS = {
    'FINDING': {'REPORT_REMAINING_RECORD': 'PRESENT', 'REPORT_EXPOSED_PII': 'PRESENT', 'REPORT_ACTIVE_DATA_FLOW': 'ACTIVE', 'REPORT_RESTORE_RISK': 'ACTIVE'},
    'REMEDIATION': {'DISABLE_DATA_FLOW': 'DISABLED', 'BLOCK_RESTORE': 'BLOCKED', 'DELETE_RECORD': 'ABSENT', 'REDACT_RECORD': 'REDACTED', 'ANONYMIZE_RECORD': 'ANONYMIZED'},
    'VERIFICATION': {'VERIFY_RECORD_ABSENT': 'ABSENT', 'VERIFY_RECORD_PRESENT': 'PRESENT', 'VERIFY_RECORD_REDACTED': 'REDACTED', 'VERIFY_RECORD_ANONYMIZED': 'ANONYMIZED', 'VERIFY_DATA_FLOW_DISABLED': 'DISABLED', 'VERIFY_RESTORE_BLOCKED': 'BLOCKED'},
}
QUESTIONS = {
    'authorization_uncertain': 'Does the request authorize deletion?',
    'identity_uncertain': 'Which stable subject does the request identify?',
    'evidence_incomplete': 'What cutoff-valid evidence is missing or requires review?',
    'conflicting_evidence': 'Which observation establishes the resource state at audit time?',
    'policy_uncertain': 'Which supplied policy condition and action apply?',
    'unsupported_citation': 'What source location proves the resource and state?',
    'invalid_model_output': 'Can the response satisfy the required reasoning schema?',
    'model_unavailable': 'Can the configured model transport complete a bounded call?',
    'untrusted_instruction': 'Can the suspicious evidence be independently inspected as data?',
    'tool_violation': 'Why did the model attempt an unavailable capability?',
}
STEP_FIELDS = {'phase', 'system_id', 'resource_id', 'operation', 'state', 'evidence_id', 'location'}


class GuardrailError(ValueError):
    def __init__(self, code: str):
        """Expose only a fixed reason code, never raw model or evidence content."""
        self.code = code
        super().__init__(code)


def packet_issues(packet: CasePacket) -> list[str]:
    """Recheck authorization, unique identity, bounds, source availability, and uncertainty."""
    issues = set()
    if packet.intent.decision != 'AUTHORIZED':
        issues.add('authorization_uncertain')
    if len({link.user_id for link in packet.identity_links}) != 1:
        issues.add('identity_uncertain')
    if packet.uncertainty or packet.omitted_facts or not packet.facts:
        issues.add('evidence_incomplete')
    if not packet.rules or any(rule.get('required_action') not in {'DELETE', 'REDACT', 'ANONYMIZE', 'RETAIN'} or not rule.get('data_category') or not rule.get('condition') for rule in packet.rules):
        issues.add('policy_uncertain')
    try:
        cutoff = timestamp(packet.audit_at)
        for link in packet.identity_links:
            if timestamp(link.observed_at) > cutoff:
                issues.add('identity_uncertain')
        for fact in packet.facts:
            if re.search(r'ignore.{0,40}(?:instructions|policy)|system prompt|</?system>|(?:invoke|call|execute).{0,20}(?:shell|bash|python|browser)', fact.text, re.I):
                issues.add('untrusted_instruction')
            if fact.uncertainty or not fact.resource_ids or not fact.system_id:
                issues.add('evidence_incomplete')
            if any(timestamp(t) > cutoff for t in (fact.captured_at, *fact.event_times)):
                issues.add('evidence_incomplete')
        if len(packet.facts) > 150 or sum(len(json.dumps(f.__dict__, ensure_ascii=False)) for f in packet.facts) > 60000:
            issues.add('evidence_incomplete')
    except (ValueError, TypeError):
        issues.add('evidence_incomplete')
    return sorted(issues)


def response_schema(packet: CasePacket) -> dict:
    """Produce a closed JSON schema with packet-derived identifier allowlists."""
    properties = {key: {'type': 'string'} for key in STEP_FIELDS}
    properties.update({
        'phase': {'enum': list(OPERATIONS)},
        'operation': {'enum': [op for ops in OPERATIONS.values() for op in ops]},
        'state': {'enum': sorted({state for ops in OPERATIONS.values() for state in ops.values()})},
        'system_id': {'enum': sorted({f.system_id for f in packet.facts if f.system_id})},
        'resource_id': {'enum': sorted({r for f in packet.facts for r in f.resource_ids})},
        'evidence_id': {'enum': ['', *sorted({f.evidence_id for f in packet.facts})]},
        'location': {'enum': ['', *sorted({f.location for f in packet.facts})]},
    })
    return {'type': 'object', 'additionalProperties': False, 'required': ['status', 'steps', 'unresolved'], 'properties': {
        'status': {'enum': ['COMPLETE', 'INCOMPLETE', 'UNCERTAIN']},
        'steps': {'type': 'array', 'maxItems': 450, 'items': {'type': 'object', 'additionalProperties': False, 'required': sorted(STEP_FIELDS), 'properties': properties}},
        'unresolved': {'type': 'array', 'uniqueItems': True, 'maxItems': len(QUESTIONS), 'items': {'enum': sorted(QUESTIONS)}},
    }}


def parse_response(raw: str) -> dict:
    """Reject oversized JSON, duplicate keys, nonstandard numbers, and nonobjects."""
    if not isinstance(raw, str) or len(raw) > 200000:
        raise GuardrailError('invalid_model_output')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise GuardrailError('invalid_model_output')
            result[key] = value
        return result
    def invalid_constant(value):
        raise GuardrailError('invalid_model_output')
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise GuardrailError('invalid_model_output') from exc
    if not isinstance(value, dict):
        raise GuardrailError('invalid_model_output')
    return value


def supports_state(text: str, operation: str, state: str) -> bool:
    """Require explicit state markers; identifier presence alone never proves a state."""
    patterns = {
        'ABSENT': r'\b(?:ABSENT|NOT_FOUND)\b|\brows[=: ]+0\b',
        'PRESENT': r'\b(?:PRESENT|FOUND|IDENTIFIABLE)\b',
        'ACTIVE': r'\bACTIVE\b', 'REDACTED': r'\bREDACTED\b',
        'ANONYMIZED': r'\bANONYMIZED\b', 'DISABLED': r'\bDISABLED\b', 'BLOCKED': r'\bBLOCKED\b',
    }
    if not re.search(patterns[state], text):
        return False
    if operation == 'REPORT_EXPOSED_PII' and not re.search(r'\b(?:IDENTIFIABLE|EXPOSED_PII)\b', text):
        return False
    # Negated assertions and multiple incompatible state markers need interpretation.
    if re.search(r'\b(?:not|never|false)\s+' + state + r'\b', text, re.I):
        return False
    opposites = {'ABSENT': ('PRESENT', 'FOUND'), 'PRESENT': ('ABSENT', 'NOT_FOUND'), 'ACTIVE': ('DISABLED', 'BLOCKED'), 'DISABLED': ('ACTIVE',), 'BLOCKED': ('ACTIVE',), 'REDACTED': ('IDENTIFIABLE',), 'ANONYMIZED': ('IDENTIFIABLE',)}
    return not any(re.search(r'\b' + word + r'\b', text) for word in opposites[state])


def validate_response(raw: str, packet: CasePacket) -> dict:
    """Check schema, exact citation/resource/system binding, phases, states, and conflicts."""
    issues = packet_issues(packet)
    if issues:
        raise GuardrailError(issues[0])
    value = parse_response(raw)
    if set(value) != {'status', 'steps', 'unresolved'} or value['status'] not in ('COMPLETE', 'INCOMPLETE', 'UNCERTAIN'):
        raise GuardrailError('invalid_model_output')
    steps, unresolved = value['steps'], value['unresolved']
    if not isinstance(steps, list) or len(steps) > 450 or not isinstance(unresolved, list) or any(not isinstance(code, str) or code not in QUESTIONS for code in unresolved) or len(set(unresolved)) != len(unresolved):
        raise GuardrailError('invalid_model_output')
    if value['status'] == 'UNCERTAIN':
        if steps or not unresolved:
            raise GuardrailError('invalid_model_output')
        return value
    if not steps or unresolved:
        raise GuardrailError('invalid_model_output')
    phases = []
    seen = set()
    for step in steps:
        if not isinstance(step, dict) or set(step) != STEP_FIELDS or any(not isinstance(v, str) for v in step.values()):
            raise GuardrailError('invalid_model_output')
        phase, operation, state = step['phase'], step['operation'], step['state']
        if phase not in OPERATIONS or OPERATIONS[phase].get(operation) != state:
            raise GuardrailError('invalid_model_output')
        phases.append(list(OPERATIONS).index(phase))
        key = (phase, step['system_id'], step['resource_id'], operation)
        if key in seen:
            raise GuardrailError('invalid_model_output')
        seen.add(key)
        resources = [f for f in packet.facts if f.system_id == step['system_id'] and step['resource_id'] in f.resource_ids]
        if not resources:
            raise GuardrailError('unsupported_citation')
        future = value['status'] == 'INCOMPLETE' and phase != 'FINDING'
        if future:
            if step['evidence_id'] or step['location']:
                raise GuardrailError('unsupported_citation')
            continue
        citations = [f for f in resources if f.evidence_id == step['evidence_id'] and f.location == step['location']]
        if len(citations) != 1 or citations[0].kind != 'observation' or citations[0].uncertainty or len(citations[0].resource_ids) != 1 or not supports_state(citations[0].text, operation, state):
            raise GuardrailError('unsupported_citation')
        for other in resources:
            if other.kind == 'observation' and other != citations[0] and any(supports_state(other.text, operation, alternative) for alternative in ('ABSENT', 'PRESENT', 'ACTIVE', 'DISABLED', 'BLOCKED', 'REDACTED', 'ANONYMIZED') if alternative != state):
                raise GuardrailError('conflicting_evidence')
    if phases != sorted(phases):
        raise GuardrailError('invalid_model_output')
    if value['status'] == 'COMPLETE' and any(step['phase'] != 'VERIFICATION' for step in steps):
        raise GuardrailError('invalid_model_output')
    if value['status'] == 'INCOMPLETE' and set(phases) != {0, 1, 2}:
        raise GuardrailError('invalid_model_output')
    if value['status'] == 'INCOMPLETE':
        findings = {(s['system_id'], s['resource_id']) for s in steps if s['phase'] == 'FINDING'}
        remediations = [s for s in steps if s['phase'] == 'REMEDIATION']
        remedies = {(s['system_id'], s['resource_id']) for s in remediations}
        verified = {(s['system_id'], s['resource_id'], s['state']) for s in steps if s['phase'] == 'VERIFICATION'}
        if findings != remedies or any((s['system_id'], s['resource_id'], s['state']) not in verified for s in remediations):
            raise GuardrailError('invalid_model_output')
    if value['status'] == 'COMPLETE':
        covered = {(s['system_id'], s['resource_id']) for s in steps}
        if any((f.system_id, resource) not in covered for f in packet.facts for resource in f.resource_ids):
            raise GuardrailError('evidence_incomplete')
    return value
