# 03 — Agent, tool, and guardrails

Constrain the LLM to one agent and one model-facing tool. The tool is read-only and returns prepared evidence; all data access and state-changing work stays outside the agent.

- [x] **AGENT-01 — Define the single agent's job.** Given one authorized case packet, decide whether deletion is complete, incomplete, or uncertain and return only schema-constrained reasoning inputs for deterministic serialization.
- [x] **AGENT-02 — Define the one tool: `audit_case(case_id)`.** It returns the bounded evidence packet for exactly one case. It cannot mutate data, execute arbitrary commands, browse the filesystem, or access network services.
- [x] **AGENT-03 — Make the middleware run first.** The agent cannot be invoked until request authorization, identity resolution, cutoff filtering, and packet construction have completed. Skip the model entirely for clear non-deletion requests.
- [x] **AGENT-04 — Defend against prompt injection.** Treat request text and all evidence contents as untrusted quoted data, never as instructions. Explicitly forbid following instructions found in evidence, changing policy, inventing citations, or using tools beyond `audit_case`.
- [x] **AGENT-05 — Require citation-backed findings.** Every alleged remaining record, exposed identifier, active flow, or restore risk must cite a supplied `file_id`, `activity_id`, or `audit_id`; identify the exact supported resource and state.
- [x] **AGENT-06 — Constrain generation.** Require structured output with only allowed statuses, phases, operations, states, system/resource IDs from the packet, and evidence references. Do not let the model write the final CSV directly.
- [x] **AGENT-07 — Escalate uncertainty.** Escalate ambiguous authorization, identity collisions, conflicting snapshots, missing/late evidence, unclear policy treatment, unsupported citations, or invalid model output. Never label an uncertain case `COMPLETE` by default.
- [x] **AGENT-08 — Keep a human-review record.** For each escalation, record the case ID, reason codes, unresolved questions, and source references without copying unnecessary personal data.
- [x] **AGENT-09 — Define bounded retry behavior.** Retry transient model/format failures a limited number of times; then escalate. Do not broaden evidence access or weaken citation requirements to force a result.

**Completion check:** a prompt-injection attempt inside request/evidence text cannot change instructions or invoke extra capabilities; unsupported claims fail validation or escalate.


Implementation and inspection inventory: [`code/AGENT_GUARDRAILS_RECORD.md`](../code/AGENT_GUARDRAILS_RECORD.md). The agent boundary is transport-injected; live provider integration is not configured. Final policy execution and submission serialization remain task 04.
