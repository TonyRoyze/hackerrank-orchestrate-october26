# 02 — Evidence pipeline

Prepare a bounded, attributable case packet before asking the model to reason.

- [x] **EVIDENCE-01 — Load and validate input tables.** Read requests, identity snapshots, audit history, activity, deletion rules, and the evidence manifest; check required columns and duplicate or missing IDs.
- [x] **EVIDENCE-02 — Implement request-first middleware.** Classify whether `request_text` authorizes deletion before retrieval or model calls. Route access, correction, export, marketing opt-out, and other non-deletion requests to `NOT_APPLICABLE` with `[]`.
- [x] **EVIDENCE-03 — Resolve identity history.** Link the supplied email to current and historical identifiers using identity snapshots and audit logs. Preserve stable `user_id`; track the evidence and confidence for every link.
- [x] **EVIDENCE-04 — Enforce the audit cutoff.** Exclude evidence and activity after `audit_at`; distinguish event time, capture time, and reported time where the sources provide them.
- [x] **EVIDENCE-05 — Build evidence parsers.** Parse text, JSON, logs, SQL snapshots, PDFs, and images/screenshots as applicable. Preserve source file IDs, resource/system IDs, extracted timestamps, and relevant text or fields.
- [x] **EVIDENCE-06 — Retrieve by grounded identifiers.** Search global evidence using current and historical emails, names, phone numbers, hashes, stable IDs, and resource references. Treat manifest metadata as a locator, not proof of case membership.
- [x] **EVIDENCE-07 — Build a bounded case packet.** Return only relevant, cutoff-valid facts with explicit provenance and uncertainty labels; keep unrelated global records and raw bulk files out of the model context.
- [x] **EVIDENCE-08 — Keep claims separate from observations.** Mark workflow status and activity results as claims unless an evidence artifact establishes actual resource state. Compare primary and replica snapshots where relevant.

**Completion check:** each packet can be audited back to source IDs and timestamps, and no post-cutoff or ungrounded evidence reaches the agent as fact.


Implementation and inspection inventory: [`code/EVIDENCE_PIPELINE_RECORD.md`](../code/EVIDENCE_PIPELINE_RECORD.md). The `packet` command implements this preparation stage; final reasoning and submission output remain later tasks.
