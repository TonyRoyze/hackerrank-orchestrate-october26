# Agent guardrails implementation record

Implements `todo/03-agent-guardrails.md`. Prior evidence-pipeline changes remain intact; no dataset or submission predictions are changed.

## Review order

1. `code/guardrails.py`: gating, closed schema, citation binding, and response validation.
2. `code/agent.py`: single-agent transport, one case tool, retries, and review records.
3. `code/main.py`: guard inspection/replay command.
4. `tests/test_guardrails.py`: synthetic adversarial boundary cases.

## `code/guardrails.py`

New file.

- `GuardrailError.__init__` (line 32): Expose only a fixed reason code, never raw model or evidence content.
- `packet_issues` (line 38): Recheck authorization, unique identity, bounds, source availability, and uncertainty.
- `response_schema` (line 68): Produce a closed JSON schema with packet-derived identifier allowlists.
- `parse_response` (line 87): Reject oversized JSON, duplicate keys, nonstandard numbers, and nonobjects.
- `parse_response.unique` (line 91): Reject duplicate object keys during JSON parsing.
- `parse_response.invalid_constant` (line 98): Reject nonstandard JSON constants.
- `supports_state` (line 109): Require explicit state markers; identifier presence alone never proves a state.
- `validate_response` (line 128): Check schema, exact citation/resource/system binding, phases, states, and conflicts.

## `code/agent.py`

New file.

- `ModelTransport.__call__` (line 37): Return JSON text; adapters must impose their own request timeout/token limit.
- `CaseTool.__init__` (line 43): Freeze prepared data before exposing the single case-scoped tool.
- `CaseTool.definition` (line 51): Expose exactly audit_case(case_id), with a one-case enum.
- `CaseTool.dispatch` (line 55): Reject arbitrary capabilities, extra arguments, cross-case access, and loops.
- `escalate` (line 81): Create a privacy-minimal review record from fixed questions and supplied IDs.
- `append_review` (line 89): Append one review event; no raw prompt, response, or personal identifiers.
- `AuditAgent.__init__` (line 96): Bind one transport and bounded retries without granting data access to it.
- `AuditAgent.audit` (line 104): Run middleware before any model invocation; gate and validate every attempt.

## `code/main.py`

Modified existing file.

- `build_parser` (line 14): Add the guard subcommand with explicit response, result, and review paths.
- `main` (line 56): Dispatch guard requests alongside existing commands.
- `_guard_case` (line 85): Inspect gated reasoning or replay a saved response without a network adapter.
- `_guard_case.replay` (line 95): Replay saved JSON after requesting the case-scoped tool; perform no network access.

## `tests/test_guardrails.py`

New file.

- `packet` (line 14): Construct a minimal authorized packet with no real personal data.
- `response` (line 19): Supply a schema-valid, explicitly cited synthetic verification.
- `runner` (line 24): Inject a recording model transport; consume bounded deterministic replies.
- `runner.transport` (line 27): Synthetic transport callback used to exercise allowed or rejected capabilities.
- `GuardrailTests.test_valid_complete_and_schema` (line 38): Regression test: valid complete and schema.
- `GuardrailTests.test_middleware_blocks_calls` (line 45): Regression test: middleware blocks calls.
- `GuardrailTests.test_tool_cross_case_and_extra_capabilities` (line 57): Regression test: tool cross case and extra capabilities.
- `GuardrailTests.test_evidence_instruction_is_quarantined` (line 62): Regression test: evidence instruction is quarantined.
- `GuardrailTests.test_tool_snapshot_and_limit` (line 69): Regression test: tool snapshot and limit.
- `GuardrailTests.test_injection_cannot_grant_tools_even_if_error_swallowed` (line 79): Regression test: injection cannot grant tools even if error swallowed.
- `GuardrailTests.test_injection_cannot_grant_tools_even_if_error_swallowed.attack` (line 81): Synthetic transport callback used to exercise allowed or rejected capabilities.
- `GuardrailTests.test_unsupported_citation_binding` (line 91): Regression test: unsupported citation binding.
- `GuardrailTests.test_claims_do_not_prove_complete` (line 98): Regression test: claims do not prove complete.
- `GuardrailTests.test_duplicate_keys_extra_fields_and_invalid_json` (line 102): Regression test: duplicate keys extra fields and invalid json.
- `GuardrailTests.test_incomplete_future_steps_and_coverage` (line 107): Regression test: incomplete future steps and coverage.
- `GuardrailTests.test_conflicting_observation` (line 121): Regression test: conflicting observation.
- `GuardrailTests.test_late_evidence_and_identity_collision` (line 127): Regression test: late evidence and identity collision.
- `GuardrailTests.test_bounded_format_and_transient_retries` (line 134): Regression test: bounded format and transient retries.
- `GuardrailTests.test_citation_failures_are_not_retried` (line 145): Regression test: citation failures are not retried.
- `GuardrailTests.test_uncertainty_requires_questions` (line 152): Regression test: uncertainty requires questions.
- `GuardrailTests.test_review_record_privacy` (line 158): Regression test: review record privacy.
- `GuardrailTests.test_invalid_retry_bounds` (line 172): Regression test: invalid retry bounds.

## Supporting files

- `README.md`: command examples, review records, transport contract, retry bounds, and remaining task 04 scope.
- `todo/03-agent-guardrails.md`: completed task checklist and link to this record.
- `log.txt`: append-only conversation summary.
- `code/AGENT_GUARDRAILS_RECORD.md`: this inspection record.

## Contracts and records

- `SYSTEM_PROMPT`: evidence is untrusted data, supplied policy is authoritative, one tool only, no final CSV generation.
- `OPERATIONS`: exact permitted phase/operation/state combinations.
- `QUESTIONS`: closed escalation-code vocabulary with fixed questions.
- `ModelTransport`: provider-neutral callable interface; not a provider SDK implementation.
- `ReviewRecord`: case ID, fixed reason codes/questions, supplied source IDs.
- `AgentResult`: accepted reasoning or uncertainty/review, plus attempted call count.
- Response object: exactly `status`, `steps`, `unresolved`; each reasoning step has phase, system/resource IDs, operation, state, evidence ID, and exact source location. No model-produced final CSV or step numbering.

## Important review limits

- Capability restrictions are enforced by the dispatcher, independent of prompt wording. The injection-pattern scan is additional conservative quarantine, not a complete natural-language injection detector. No claim is made that prompt text alone can guarantee semantic correctness.
- Transport implementations are trusted host code. The supplied model-facing callback has no filesystem, network, arbitrary command, or mutation operation; offline replay reads its response outside that callback.
- Middleware rejects any packet uncertainty, missing system/resource attribution, post-cutoff evidence, or missing/unknown policy actions. This may escalate otherwise answerable cases.
- Explicit observation-state markers are required. Claims, OCR-review flags, name-only matches, multiple-resource citations, and unsupported/inferred states cannot prove a final answer. Structured JSON records without explicit state markers may therefore require review.
- Conflicting observations escalate conservatively even if timestamp ordering could resolve the difference. This stage does not implement the task 04 policy solver or replica state reconstruction.
- The validator enforces phase order and resource coverage; task 04 still owns deterministic policy treatment, operation ordering within phases, numbering, and final CSV serialization.
- Retry count bounds attempts, not wall-clock time: each future live provider adapter must set request timeout/output-token limits. There is no live provider integration or production-model accuracy claim in this change.
- Library callers receive review records in `AgentResult`; the CLI persists each escalation through `append_review`. Callers integrating the library must persist returned records.

## Verification

- `python3 -m unittest discover -s tests -v`: 26 tests pass (17 guardrail tests plus 9 evidence-pipeline tests).
- Guard CLI smoke: case_33 escalates before a model call because middleware finds incomplete attribution. Result and append-only review event are written to explicit temporary paths; exit code is 2.
- Tests cover accepted complete/incomplete responses, fixed-schema failures, exact citation binding, uncertainty, conflicts, late evidence, identity collisions, injection quarantine, capability violations (including swallowed errors), bounded retries, non-deletion skipping, tool snapshots, and review privacy.

