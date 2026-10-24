# 05 — Evaluation and submission

Measure correctness, record token use, document operation, and prepare the requested artifacts only from the finished run.

- [ ] **EVAL-01 — Reproduce the public sample.** Run the implementation against `sample_deletion_requests.csv` and compare its output with `sample_output.csv`; investigate every mismatch.
- [ ] **EVAL-02 — Add at least three participant-created evaluation cases.** Cover non-deletion authorization, historical identity, late evidence cutoff, policy-retained/tombstone data, injection text, or active recreation risk.
- [ ] **EVAL-03 — Measure quality.** Record case-level status accuracy, step-level and field-level accuracy, and sequence accuracy using only permitted evaluation material. Explain the metric and denominator.
- [ ] **EVAL-04 — Record failures and improvements.** Document concrete errors found during evaluation and the changes made to address them.
- [ ] **EVAL-05 — Write `evaluation/evaluation_report.md`.** Include all required metrics, custom cases, failures, and improvements.
- [ ] **EVAL-06 — Run the final full dataset.** Produce root `output.csv` for all 518 cases and retain run metadata needed by the usage report.
- [ ] **EVAL-07 — Write `evaluation/usage_report.md`.** Include providers/models, call counts, input/output/total/average tokens, estimated total/per-request cost, and per-model plus overall totals.
- [ ] **SUBMISSION-01 — Write setup and run instructions.** Update `README.md` with prerequisites, environment configuration, full run command, one-case command, outputs, and evaluation/report paths.
- [ ] **SUBMISSION-02 — Build `code.zip`.** Include runnable code, prompts/configuration, README, and evaluation reports. Exclude `dataset/`, virtual environments, caches, nested archives, credentials, and sensitive configuration.
- [ ] **SUBMISSION-03 — Stage the agent trace.** After the relevant sessions are finished and the harness is closed, copy only challenge-related traces into tool-specific subfolders under `agent-trace/`; preserve structured formats where practical.
- [ ] **SUBMISSION-04 — Review and sanitize traces.** Inspect staged traces for secrets, personal information, unrelated sessions, and disallowed material; redact or remove before packaging.
- [ ] **SUBMISSION-05 — Create and inspect `agent-trace.zip`.** Confirm it contains the intended trace files and no credentials or unrelated data.
- [ ] **SUBMISSION-06 — Final artifact check.** Confirm `output.csv`, `code.zip`, and `agent-trace.zip` are present and meet their respective requirements.

**Completion check:** reports accurately describe the final run, archives contain only allowed files, and all requested artifacts are ready for submission.

