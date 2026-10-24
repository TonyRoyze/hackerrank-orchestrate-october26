"""Typed records shared by the deletion-audit pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


DeletionStatus = Literal["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"]
Phase = Literal["FINDING", "REMEDIATION", "VERIFICATION"]


@dataclass(frozen=True)
class DeletionRequest:
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime | None
    audit_at: datetime
    request_text: str


@dataclass(frozen=True)
class Identity:
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: datetime | None = None


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    path: str
    source_origin: str
    captured_at: datetime | None = None


@dataclass(frozen=True)
class PolicyRule:
    category: str
    condition: str
    action: str
    details: str = ""


@dataclass(frozen=True)
class AuditFinding:
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str


@dataclass(frozen=True)
class PlannedStep:
    step_no: int
    phase: Phase
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str


@dataclass(frozen=True)
class Escalation:
    case_id: str
    reason_code: str
    explanation: str
    evidence_ids: tuple[str, ...] = ()


@dataclass
class RunMetadata:
    provider: str | None = None
    model: str | None = None
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    estimated_cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def average_tokens_per_request(self) -> float:
        return self.total_tokens / self.requests_processed if self.requests_processed else 0.0

    requests_processed: int = 0

    def record_model_call(self, input_tokens: int, output_tokens: int) -> None:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts cannot be negative")
        self.model_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def estimate_cost(self, input_usd_per_million: float, output_usd_per_million: float) -> float:
        if input_usd_per_million < 0 or output_usd_per_million < 0:
            raise ValueError("Token prices cannot be negative")
        self.estimated_cost_usd = (
            self.input_tokens * input_usd_per_million
            + self.output_tokens * output_usd_per_million
        ) / 1_000_000
        return self.estimated_cost_usd

