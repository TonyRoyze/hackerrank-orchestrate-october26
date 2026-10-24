# 01 — Foundation

Keep the implementation runnable, deterministic, and within the challenge's participant-data boundary.

- [x] **FOUNDATION-01 — Choose the implementation stack.** Python's standard library is the initial stack; setup and run commands are documented in `README.md`.
- [x] **FOUNDATION-02 — Define repository boundaries.** Request input defaults to the repository's `dataset/`; dataset and output paths are rooted from the code location. No organizer-only sources are referenced.
- [x] **FOUNDATION-03 — Add configuration handling.** Provider, model, API key, and optional token prices are read from environment variables; secret values are never printed.
- [x] **FOUNDATION-04 — Create the terminal entry point.** `python3 -m code.main run` preflights the full dataset; `python3 -m code.main case CASE_ID` inspects one case without printing its email or request text.
- [x] **FOUNDATION-05 — Define typed internal records.** Added records for requests, identities, evidence, policy rules, findings, planned steps, escalations, and run metadata.
- [x] **FOUNDATION-06 — Add run metadata collection.** Added counters and helpers for model calls, token totals, average tokens per request, timestamps, and token-based cost estimates.

**Completion check:** the foundation CLI starts from the documented command, resolves default input paths independently of the current working directory, and reports missing or malformed inputs clearly. Model credential validation is exposed for the integration stage; these preflight commands do not require model credentials.

