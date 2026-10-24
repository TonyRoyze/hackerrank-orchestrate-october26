# 04 — Policy, output, and operations

Use ordinary code for predictable decisions and formatting. The model should not do sorting, step numbering, CSV escaping, policy lookup, or schema checks.

- [ ] **OUTPUT-01 — Encode policy actions.** Apply `deletion_rules.csv` to every relevant resource, including retained records, redaction/anonymization, and account tombstones.
- [ ] **OUTPUT-02 — Preserve tombstone semantics.** Keep the permitted stable subject reference while requiring removal of direct identifiers covered by the applicable redaction rule.
- [ ] **OUTPUT-03 — Plan safe remediation order.** Disable active data flows and block unsafe restores before dependent changes; process downstream copies before their source where required.
- [ ] **OUTPUT-04 — Generate findings and future steps.** For `INCOMPLETE`, include all supported findings, complete remediation, then verification for each remediated resource/process. Use empty evidence IDs for proposed work and future checks.
- [ ] **OUTPUT-05 — Generate complete-case verification.** For `COMPLETE`, include only checks supported by evidence at or before `audit_at`; include retained-record checks where policy requires them.
- [ ] **OUTPUT-06 — Keep operation ordering deterministic.** Order by phase, then the contract's operation order, then `system_id` and `resource_id`; number steps consecutively from 1.
- [ ] **OUTPUT-07 — Validate every step.** Enforce exact fields, allowed phase/operation/state combinations, citation validity, cutoff validity, evidence-ID rules, and consecutive numbering. Reject unsupported model output.
- [ ] **OUTPUT-08 — Serialize the submission CSV.** Write root `output.csv` with exactly `case_id,deletion_status,steps_json`, one row per request, sorted by `case_id`; JSON-encode arrays safely for CSV.
- [ ] **OUTPUT-09 — Add run summary and review output.** Report counts by status, escalations, malformed inputs, model failures, and output row count without exposing secrets or unnecessary personal data.

**Completion check:** output passes contract validation and contains exactly one valid row for every request.

