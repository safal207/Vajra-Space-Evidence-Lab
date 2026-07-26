from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Iterable

from .bundle import validate_bundle_file
from .ledger import append_record, validate_ledger_file
from .renderer import render_claim_markdown
from .reports import build_report, encode_report
from .reproduction import (
    run_reproduction,
    validate_reproduction_manifest,
    verify_attestation_hmac,
)
from .scoring import calculate_evidence_level
from .validator import validate_claim_file, validate_evidence_file


REPRODUCTION_EXIT_CODES = {
    "success": 0,
    "partial": 2,
    "mismatch": 3,
    "blocked": 4,
}


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit a stable versioned JSON report.",
    )


def _human_issues(issues: Iterable[Any]) -> None:
    for issue in issues:
        if isinstance(issue, dict):
            print(f"{issue.get('code', 'error')}: {issue.get('path', '$')}: {issue.get('message', '')}")
        elif isinstance(issue, str):
            print(issue)
        else:
            print(f"{issue.code}: {issue.path}: {issue.message}")


def _emit_validation(
    *,
    command: str,
    input_path: Path,
    valid: bool,
    issues: Iterable[Any],
    json_output: bool,
    data: Any = None,
) -> int:
    materialized_issues = list(issues)
    if json_output:
        report = build_report(
            command=command,
            input_path=input_path,
            status="valid" if valid else "invalid",
            issues=materialized_issues,
            data=data,
        )
        print(encode_report(report), end="")
    elif valid:
        print("VALID")
    else:
        _human_issues(materialized_issues)
    return 0 if valid else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="vajra-space")
    sub = parser.add_subparsers(dest="command", required=True)

    claim = sub.add_parser("validate-claim")
    claim.add_argument("claim")
    claim.add_argument("--schema", default="schemas/claim.schema.json")
    _add_json_flag(claim)

    evidence = sub.add_parser("validate-evidence")
    evidence.add_argument("evidence")
    evidence.add_argument("--schema", default="schemas/evidence.schema.json")
    _add_json_flag(evidence)

    bundle = sub.add_parser("validate-bundle")
    bundle.add_argument("bundle")
    bundle.add_argument("--schema", default="schemas/bundle.schema.json")
    _add_json_flag(bundle)

    reproduction_manifest = sub.add_parser("validate-reproduction-manifest")
    reproduction_manifest.add_argument("manifest")
    reproduction_manifest.add_argument("--schema", default="schemas/reproduction.schema.json")
    _add_json_flag(reproduction_manifest)

    reproduce = sub.add_parser("reproduce")
    reproduce.add_argument("manifest")
    reproduce.add_argument("--schema", default="schemas/reproduction.schema.json")
    reproduce.add_argument("--workspace", default=".")
    reproduce.add_argument("--execute", action="store_true")
    reproduce.add_argument("--attestation")
    reproduce.add_argument("--signing-key-env")
    reproduce.add_argument("--key-id")
    _add_json_flag(reproduce)

    verify_reproduction = sub.add_parser("verify-reproduction-attestation")
    verify_reproduction.add_argument("attestation")
    verify_reproduction.add_argument("--signing-key-env", required=True)
    _add_json_flag(verify_reproduction)

    score = sub.add_parser("score-evidence")
    score.add_argument("bundle")

    append = sub.add_parser("ledger-append")
    append.add_argument("ledger")
    append.add_argument("claim")
    append.add_argument("--event-type", default="assessment")
    append.add_argument("--actor", required=True)

    ledger = sub.add_parser("ledger-validate")
    ledger.add_argument("ledger")
    _add_json_flag(ledger)

    render = sub.add_parser("render-claim")
    render.add_argument("claim")
    render.add_argument("--output")

    args = parser.parse_args()

    if args.command == "validate-claim":
        input_path = Path(args.claim)
        result = validate_claim_file(input_path, Path(args.schema))
        return _emit_validation(
            command=args.command,
            input_path=input_path,
            valid=result.valid,
            issues=result.issues,
            json_output=args.json_output,
        )

    if args.command == "validate-evidence":
        input_path = Path(args.evidence)
        result = validate_evidence_file(input_path, Path(args.schema))
        return _emit_validation(
            command=args.command,
            input_path=input_path,
            valid=result.valid,
            issues=result.issues,
            json_output=args.json_output,
        )

    if args.command == "validate-bundle":
        input_path = Path(args.bundle)
        result = validate_bundle_file(input_path, Path(args.schema))
        return _emit_validation(
            command=args.command,
            input_path=input_path,
            valid=result.valid,
            issues=result.issues,
            json_output=args.json_output,
        )

    if args.command == "validate-reproduction-manifest":
        input_path = Path(args.manifest)
        manifest = json.loads(input_path.read_text(encoding="utf-8"))
        schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        issues = validate_reproduction_manifest(manifest, schema)
        return _emit_validation(
            command=args.command,
            input_path=input_path,
            valid=not issues,
            issues=issues,
            json_output=args.json_output,
        )

    if args.command == "reproduce":
        input_path = Path(args.manifest)
        signing_key: bytes | None = None
        if args.signing_key_env:
            value = os.environ.get(args.signing_key_env)
            if value is None:
                issues = [{
                    "code": "missing_signing_key",
                    "path": "$.signing_key",
                    "message": f"Environment variable is not set: {args.signing_key_env}",
                }]
                if args.json_output:
                    report = build_report(
                        command=args.command,
                        input_path=input_path,
                        status="blocked",
                        issues=issues,
                    )
                    print(encode_report(report), end="")
                else:
                    print(json.dumps({"status": "blocked", "issues": issues}, indent=2))
                return REPRODUCTION_EXIT_CODES["blocked"]
            signing_key = value.encode("utf-8")

        reproduction_result = run_reproduction(
            input_path,
            Path(args.schema),
            Path(args.workspace),
            allow_execution=args.execute,
            signing_key=signing_key,
            key_id=args.key_id,
        )
        attestation_payload = json.dumps(
            reproduction_result.attestation,
            indent=2,
            sort_keys=True,
        ) + "\n"
        if args.attestation:
            Path(args.attestation).write_text(attestation_payload, encoding="utf-8")

        if args.json_output:
            report = build_report(
                command=args.command,
                input_path=input_path,
                status=reproduction_result.status,
                issues=reproduction_result.attestation.get("issues", []),
                data={"attestation": reproduction_result.attestation},
            )
            print(encode_report(report), end="")
        else:
            print(attestation_payload, end="")
        return REPRODUCTION_EXIT_CODES[reproduction_result.status]

    if args.command == "verify-reproduction-attestation":
        input_path = Path(args.attestation)
        value = os.environ.get(args.signing_key_env)
        if value is None:
            issues = [{
                "code": "missing_signing_key",
                "path": "$.signing_key",
                "message": f"Environment variable is not set: {args.signing_key_env}",
            }]
            if args.json_output:
                report = build_report(
                    command=args.command,
                    input_path=input_path,
                    status="invalid",
                    issues=issues,
                )
                print(encode_report(report), end="")
            else:
                print(f"Missing environment variable: {args.signing_key_env}")
            return 1

        attestation = json.loads(input_path.read_text(encoding="utf-8"))
        valid = verify_attestation_hmac(attestation, value.encode("utf-8"))
        issues = [] if valid else [{
            "code": "invalid_hmac",
            "path": "$.authentication",
            "message": "HMAC-SHA256 attestation verification failed.",
        }]
        return _emit_validation(
            command=args.command,
            input_path=input_path,
            valid=valid,
            issues=issues,
            json_output=args.json_output,
            data={"algorithm": "hmac-sha256"},
        )

    if args.command == "score-evidence":
        assessment_input = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        assessment = calculate_evidence_level(assessment_input)
        print(json.dumps({"level": assessment.level, "reasons": assessment.reasons}, indent=2))
        return 0

    if args.command == "ledger-append":
        claim_data = json.loads(Path(args.claim).read_text(encoding="utf-8"))
        record = append_record(
            Path(args.ledger),
            claim_data,
            event_type=args.event_type,
            actor=args.actor,
        )
        print(json.dumps(record, indent=2))
        return 0

    if args.command == "ledger-validate":
        input_path = Path(args.ledger)
        result = validate_ledger_file(input_path)
        issues = [
            {
                "code": "ledger_error",
                "path": f"$.errors.{index}",
                "message": error,
            }
            for index, error in enumerate(result.errors)
        ]
        return _emit_validation(
            command=args.command,
            input_path=input_path,
            valid=result.valid,
            issues=issues,
            json_output=args.json_output,
        )

    claim_data = json.loads(Path(args.claim).read_text(encoding="utf-8"))
    markdown = render_claim_markdown(claim_data)
    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
