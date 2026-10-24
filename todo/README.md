# Ghost Data Still Exists — build checklist

Use this folder as the task index for the terminal-based audit agent. Task IDs are stable references for future chats; for example, ask to work on `AGENT-03` or review `EVIDENCE-02`.

## Project goal

Build a runnable terminal agent that processes all 518 requests and writes the required root `output.csv`. Keep one agent and one model-facing tool. Middleware reads and classifies each request before the agent runs. Deterministic code handles routine parsing, matching, policy lookup, ordering, serialization, and validation. The model reasons only over bounded evidence; uncertain cases are escalated instead of guessed.

## Task files

| Area | File | Scope |
| --- | --- | --- |
| Foundation | [01-foundation.md](01-foundation.md) | Runtime, repository boundaries, CLI skeleton, configuration |
| Evidence pipeline | [02-evidence-pipeline.md](02-evidence-pipeline.md) | Request middleware, identity resolution, parsing, temporal evidence retrieval |
| Agent and guardrails | [03-agent-guardrails.md](03-agent-guardrails.md) | One agent, one tool, prompt injection defenses, citations, escalation |
| Output and operations | [04-output-and-operations.md](04-output-and-operations.md) | Policy decisions, step planning, validation, deterministic CSV |
| Evaluation and submission | [05-evaluation-and-submission.md](05-evaluation-and-submission.md) | Quality evaluation, token report, README, ZIP, trace package |

## Suggested order

1. Complete `FOUNDATION-*` and decide the model/provider configuration.
2. Build `EVIDENCE-*` so the agent receives grounded, time-bounded facts.
3. Implement `AGENT-*` and `ESCALATION-*` over that evidence packet.
4. Implement `OUTPUT-*`, then evaluate end-to-end.
5. Finish `SUBMISSION-*` only after the final run and session traces are ready.

## Definition of done

- [ ] `python3` (or the documented runtime command) runs from a clean checkout using only participant-facing `dataset/` inputs.
- [ ] Every request is handled once; root `output.csv` has exactly 518 data rows, sorted by `case_id`, with the required header and valid `steps_json`.
- [ ] Non-deletion requests return `NOT_APPLICABLE` and `[]` without a model call.
- [ ] Every finding and completed-case verification is supported by a participant-visible citation no later than `audit_at`.
- [ ] Incomplete-case remediation and future verification use empty evidence IDs and comply with policy and dependency ordering.
- [ ] Ambiguous cases are surfaced for review rather than silently labeled complete.
- [ ] Required evaluation and usage reports, run instructions, and a sanitized agent trace ZIP are prepared.

## How to reference this checklist in chat

- “Implement `EVIDENCE-03` from `todo/02-evidence-pipeline.md`.”
- “Review all unchecked `AGENT-*` items in `todo/03-agent-guardrails.md`.”
- “Update the status of `SUBMISSION-02` in `todo/05-evaluation-and-submission.md`.”

