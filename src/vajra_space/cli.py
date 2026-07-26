from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .bundle import validate_bundle_file
from .ledger import append_record, validate_ledger_file
from .renderer import render_claim_markdown
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


def main() -> int:
    parser = argparse.ArgumentParser(prog="vajra-space")
    sub = parser.add_subparsers(dest="command", required=True)

    claim = sub.add_parser("validate-claim")
    claim.add_argument("claim")
    claim.add_argument("--schema", default="schemas/claim.schema.json")

    evidence = sub.add_parser("validate-evidence")
    evidence.add_argument("evidence")
    evidence.add_argument("--schema", default="schemas/evidence.schema.json")

    bundle = sub.add_parser("validate-bundle")
    bundle.add_argument("bundle")
    bundle.add_argument("--schema", default="schemas/bundle.schema.json")

    reproduction_manifest = sub.add_parser("validate-reproduction-manifest")
    reproduction_manifest.add_argument("manifest")
    reproduction_manifest.add_argument("--schema", default="schemas/reproduction.schema.json")

    reproduce = sub.add_parser("reproduce")
    reproduce.add_argument("manifest")
    reproduce.add_argument("--schema", default="schemas/reproduction.schema.json")
    reproduce.add_argument("--workspace", default=".")
    reproduce.add_argument("--execute", action="store_true")
    reproduce.add_argument("--attestation")
    reproduce.add_argument("--signing-key-env")
    reproduce.add_argument("--key-id")

    verify_reproduction = sub.add_parser("verify-reproduction-attestation")
    verify_reproduction.add_argument("attestation")
    verify_reproduction.add_argument("--signing-key-env", required=True)

    score = sub.add_parser("score-evidence")
    score.add_argument("bundle")

    append = sub.add_parser("ledger-append")
    append.add_argument("ledger")
    append.add_argument("claim")
    append.add_argument("--event-type", default="assessment")
    append.add_argument("--actor", required=True)

    ledger = sub.add_parser("ledger-validate")
    ledger.add_argument("ledger")

    render = sub.add_parser("render-claim")
    render.add_argument("claim")
    render.add_argument("--output")

    args = parser.parse_args()

    if args.command == "validate-claim":
        result = validate_claim_file(Path(args.claim), Path(args.schema))
    elif args.command == "validate-evidence":
        result = validate_evidence_file(Path(args.evidence), Path(args.schema))
    elif args.command == "validate-bundle":
        bundle_result = validate_bundle_file(Path(args.bundle), Path(args.schema))
        if bundle_result.valid:
            print("VALID")
            return 0
        for issue in bundle_result.issues:
            print(f"{issue.code}: {issue.path}: {issue.message}")
        return 1
    elif args.command == "validate-reproduction-manifest":
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        issues = validate_reproduction_manifest(manifest, schema)
        if not issues:
            print("VALID")
            return 0
        for issue in issues:
            print(f"{issue['code']}: {issue['path']}: {issue['message']}")
        return 1
    elif args.command == "reproduce":
        signing_key: bytes | None = None
        if args.signing_key_env:
            value = os.environ.get(args.signing_key_env)
            if value is None:
                print(json.dumps({
                    "status": "blocked",
                    "issues": [{
                        "code": "missing_signing_key",
                        "path": "$.signing_key",
                        "message": f"Environment variable is not set: {args.signing_key_env}",
                    }],
                }, indent=2))
                return REPRODUCTION_EXIT_CODES["blocked"]
            signing_key = value.encode("utf-8")
        reproduction_result = run_reproduction(
            Path(args.manifest),
            Path(args.schema),
            Path(args.workspace),
            allow_execution=args.execute,
            signing_key=signing_key,
            key_id=args.key_id,
        )
        payload = json.dumps(reproduction_result.attestation, indent=2, sort_keys=True) + "\n"
        if args.attestation:
            Path(args.attestation).write_text(payload, encoding="utf-8")
        print(payload, end="")
        return REPRODUCTION_EXIT_CODES[reproduction_result.status]
    elif args.command == "verify-reproduction-attestation":
        value = os.environ.get(args.signing_key_env)
        if value is None:
            print(f"Missing environment variable: {args.signing_key_env}")
            return 1
        attestation = json.loads(Path(args.attestation).read_text(encoding="utf-8"))
        if verify_attestation_hmac(attestation, value.encode("utf-8")):
            print("VALID")
            return 0
        print("INVALID")
        return 1
    elif args.command == "score-evidence":
        assessment_input = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        assessment = calculate_evidence_level(assessment_input)
        print(json.dumps({"level": assessment.level, "reasons": assessment.reasons}, indent=2))
        return 0
    elif args.command == "ledger-append":
        claim_data = json.loads(Path(args.claim).read_text(encoding="utf-8"))
        print(json.dumps(append_record(Path(args.ledger), claim_data, event_type=args.event_type, actor=args.actor), indent=2))
        return 0
    elif args.command == "ledger-validate":
        ledger_result = validate_ledger_file(Path(args.ledger))
        if ledger_result.valid:
            print("VALID")
            return 0
        print("\n".join(ledger_result.errors))
        return 1
    else:
        claim_data = json.loads(Path(args.claim).read_text(encoding="utf-8"))
        markdown = render_claim_markdown(claim_data)
        if args.output:
            Path(args.output).write_text(markdown, encoding="utf-8")
        else:
            print(markdown)
        return 0

    if result.valid:
        print("VALID")
        return 0
    for issue in result.issues:
        print(f"{issue.code}: {issue.path}: {issue.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
