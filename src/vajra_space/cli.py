from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bundle import validate_bundle_file
from .ledger import append_record, validate_ledger_file
from .renderer import render_claim_markdown
from .scoring import calculate_evidence_level
from .validator import validate_claim_file, validate_evidence_file


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
