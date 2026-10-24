# Evidence pipeline implementation record

Implements `todo/02-evidence-pipeline.md`. This inventory covers each Python function written or changed and every supporting file. Dataset files and final predictions are unchanged.

## Review order

1. `code/inputs.py`: table validation.
2. `code/pipeline.py`: intent, identity, cutoff, retrieval, and packet bounds.
3. `code/evidence.py`: extraction and provenance.
4. `tests/test_pipeline.py`: synthetic boundary tests.
5. `code/main.py`: `packet` CLI integration.

## `code/evidence.py`

New file.

- `timestamp` (line 16): Normalize ISO timestamps; reject ambiguous timezone-free inputs.
- `make_fact` (line 37): Attach manifest availability and all explicit record timestamps.
- `json_facts` (line 44): Split nested bundles at resource records, inheriting snapshot context only.
- `sql_values` (line 64): Read SQLite literal tuples without running statements or loading extensions.
- `parse_file` (line 70): Extract JSON, SQL rows, trace-linked logs, text, PDF pages, or OCR lines.

## `code/pipeline.py`

New file.

- `classify_request` (line 22): Conservatively recognize explicit deletion and explicit non-deletion intent.
- `resolve_identity` (line 48): Use only snapshots and history available by cutoff; keep ambiguous users separate.
- `identifier_pattern` (line 75): Cache one boundary-aware search expression per identifier set.
- `matches` (line 81): Match complete identifiers, never user_1 inside user_10 or email substrings.
- `before_cutoff` (line 87): Require manifest availability and every explicit event time to precede audit.
- `to_json` (line 105): Serialize deterministically for inspection or later model integration.
- `__init__` (line 111): Load participant tables; parse artifacts lazily after intent authorization.
- `packet` (line 121): Build grounded closure over resource IDs, keeping claims labeled and bounded.

## `code/inputs.py`

Modified existing file; unchanged functions are omitted.

- `load_requests` (line 27): Validate and parse request data, rejecting ambiguous or malformed input.
- `_parse_datetime` (line 77): Validate and parse request data, rejecting ambiguous or malformed input.
- `_parse_optional_datetime` (line 86): Validate and parse request data, rejecting ambiguous or malformed input.
- `load_tables` (line 107): Validate schemas, unique IDs, foreign keys, timestamps, and evidence paths.

## `code/main.py`

Modified existing file; unchanged functions are omitted.

- `build_parser` (line 14): Configure command-line arguments, including explicit packet output.
- `main` (line 50): Dispatch CLI commands and report packet/input errors.

## `tests/test_pipeline.py`

New file.

- `request` (line 13): Create the synthetic deletion request shared by tests.
- `test_table_validation` (line 18): Synthetic regression test for table validation.
- `test_intent_boundaries` (line 31): Synthetic regression test for intent boundaries.
- `test_exact_identifier_boundaries` (line 38): Synthetic regression test for exact identifier boundaries.
- `test_manifest_and_event_cutoffs` (line 42): Synthetic regression test for manifest and event cutoffs.
- `test_record_level_json` (line 48): Synthetic regression test for record level json.
- `test_historical_identity_excludes_future` (line 55): Synthetic regression test for historical identity excludes future.
- `test_non_deletion_skips_retrieval` (line 62): Synthetic regression test for non deletion skips retrieval.
- `test_trace_link_and_sql_topology` (line 69): Synthetic regression test for trace link and sql topology.
- `test_packet_resource_closure_and_budget` (line 85): Synthetic regression test for packet resource closure and budget.

## Supporting files

- `README.md`: packet command, Python/system dependencies, bounds, and remaining integration scope.
- `todo/02-evidence-pipeline.md`: checklist completion and reference to this record.
- `log.txt`: append-only session and conversation record.
- `code/EVIDENCE_PIPELINE_RECORD.md`: this inspection inventory.

## Data structures

- `Fact`: source ID/location, capture and event timestamps, system/resource references, observation/claim kind, text, and uncertainty. SQL table names preserve primary/replica distinction.
- `Intent`: authorized, non-applicable, or uncertain decision with reason.
- `IdentityLink`: stable user, identifier, source row, timestamp, and confidence.
- `CasePacket`: decision gate, identity links, policy rules, facts, explicit truncation, and uncertainty.

## Known limits to inspect

- Intent recognition is deterministic and supports the supplied request languages, not arbitrary natural language. Unrecognized language is uncertain and stops retrieval.
- Strict capture cutoffs exclude later bundle exports even when individual rows describe an earlier state. Future snapshots are not used to infer past identifiers.
- Name-only matches carry an uncertainty and do not expand the resource closure. Exact identifiers can still be shared in real-world datasets; downstream reasoning must assess attribution.
- Logs and workflow/activity results remain claims. Record artifacts are observations of a particular source at a particular time, not deletion verdicts. Replica records are preserved independently; the later reasoning stage must compare them.
- PDF/OCR extraction is line-based and marked for review. Multi-line document associations, OCR inaccuracies, and scanned PDFs without extractable text may require follow-up. No visual-state inference is attempted.
- SQL parsing supports the supplied one-line INSERT VALUES dump format. It does not execute SQL or infer record absence from a missing INSERT.
- A truncated packet or extraction failure must be resolved before a complete deletion verdict. Bounds apply to serialized facts, with identity/policy/envelope overhead documented in README.

## Verification

- `python3 -m unittest discover -s tests -v`: 9 synthetic tests pass.
- CLI smoke check: `python3 -m code.main packet case_33 --output /tmp/ghost-packet.json` produced an attributable packet without model calls.
- Full participant request sweep: all 518 evaluation requests plus 32 public requests processed; all 94 artifacts parsed. Asserted every included fact meets its audit cutoff and every packet stays within the fact-count limit. Sweep intent counts: 540 authorized and 10 non-applicable. This checks packet preparation, not deletion-prediction accuracy.

