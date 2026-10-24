"""Command-line entry point for the Ghost Data Still Exists auditor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .inputs import InputError, load_requests
from .models import DeletionRequest, RunMetadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghost-audit",
        description="Terminal entry point for the Ghost Data Still Exists audit agent.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="preflight the full request dataset")
    run_parser.add_argument(
        "--input",
        type=Path,
        default=Settings().dataset_dir / "deletion_requests.csv",
        help="participant-facing request CSV (defaults to dataset/deletion_requests.csv)",
    )
    run_parser.add_argument(
        "--expected-rows",
        type=int,
        default=518,
        help="expected request count for the full challenge run (default: 518)",
    )

    case_parser = subparsers.add_parser("case", help="inspect one request's non-sensitive metadata")
    case_parser.add_argument("case_id", help="case ID from the request CSV")
    case_parser.add_argument(
        "--input",
        type=Path,
        default=Settings().dataset_dir / "deletion_requests.csv",
        help="participant-facing request CSV (defaults to dataset/deletion_requests.csv)",
    )
    packet_parser = subparsers.add_parser("packet", help="build a bounded evidence packet (no model calls)")
    packet_parser.add_argument("case_id")
    packet_parser.add_argument("--input", type=Path, default=Settings().dataset_dir / "deletion_requests.csv")
    packet_parser.add_argument("--output", type=Path, required=True, help="explicit destination; contains fictional subject identifiers")
    guard_parser = subparsers.add_parser("guard", help="inspect guardrails or validate a saved model response")
    guard_parser.add_argument("case_id")
    guard_parser.add_argument("--input", type=Path, default=Settings().dataset_dir / "deletion_requests.csv")
    guard_parser.add_argument("--response", type=Path, help="saved JSON reasoning response; no live provider call")
    guard_parser.add_argument("--output", type=Path, required=True)
    guard_parser.add_argument("--review-log", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        requests = load_requests(args.input.resolve())
    except InputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    if args.command == "guard":
        return _guard_case(args, requests)
    if args.command == "packet":
        from .pipeline import EvidencePipeline
        request = next((item for item in requests if item.case_id == args.case_id), None)
        if request is None:
            print(f"Case not found: {args.case_id}", file=sys.stderr)
            return 2
        try:
            packet = EvidencePipeline(args.input.resolve().parent).packet(request)
            args.output.write_text(packet.to_json() + "\n", encoding="utf-8")
        except (InputError, ValueError, OSError) as exc:
            print(f"Packet error: {exc}", file=sys.stderr)
            return 2
        print(f"Packet written: {len(packet.facts)} facts; {len(packet.uncertainty)} uncertainties.")
        return 0
    if args.command == "case":
        return _show_case(args.case_id, requests)
    return _preflight_run(requests, args.expected_rows)


def _guard_case(args: argparse.Namespace, requests: list[DeletionRequest]) -> int:
    """Inspect gated reasoning or replay a saved response without a network adapter."""
    import json
    from dataclasses import asdict
    from .agent import AuditAgent, TransientModelError, append_review
    from .pipeline import EvidencePipeline
    request = next((item for item in requests if item.case_id == args.case_id), None)
    if request is None:
        print(f"Case not found: {args.case_id}", file=sys.stderr)
        return 2
    def replay(**kwargs):
        kwargs['call_tool']('audit_case', {'case_id': kwargs['case_id']})
        if args.response is None:
            raise TransientModelError('No saved response supplied')
        return args.response.read_text(encoding='utf-8')
    try:
        result = AuditAgent(EvidencePipeline(args.input.resolve().parent), replay, max_attempts=1).audit(request)
        if result.review:
            append_review(args.review_log, result.review)
        args.output.write_text(json.dumps(asdict(result), sort_keys=True, indent=2) + "\n", encoding='utf-8')
    except (InputError, ValueError, OSError) as exc:
        print(f"Guard command failed ({type(exc).__name__}).", file=sys.stderr)
        return 2
    print(f"Guard result: {result.status}; attempts: {result.attempts}.")
    return 2 if result.review else 0


def _show_case(case_id: str, requests: list[DeletionRequest]) -> int:
    request = next((item for item in requests if item.case_id == case_id), None)
    if request is None:
        print(f"Case not found: {case_id}", file=sys.stderr)
        return 2
    print(f"case_id: {request.case_id}")
    print(f"requested_at: {request.requested_at.isoformat()}")
    print(f"reported_status (claim): {request.reported_status}")
    print(f"audit_at: {request.audit_at.isoformat()}")
    print(f"request_text_chars: {len(request.request_text)}")
    print("audit_status: not evaluated (request middleware is not implemented yet)")
    return 0


def _preflight_run(requests: list[DeletionRequest], expected_rows: int) -> int:
    if expected_rows < 1:
        print("Input error: --expected-rows must be positive", file=sys.stderr)
        return 2
    if len(requests) != expected_rows:
        print(
            f"Input error: expected {expected_rows} requests, found {len(requests)}.",
            file=sys.stderr,
        )
        return 2
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    metadata = RunMetadata(
        provider=settings.provider,
        model=settings.model,
        requests_processed=len(requests),
    )
    print(f"Input preflight passed: {len(requests)} requests.")
    print(f"Model calls so far: {metadata.model_calls}.")
    print("Prediction pipeline is not implemented yet; no output.csv was written.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
