#!/usr/bin/env python3
"""Validate Unified Evidence Record (UER) files.

Checks:
1. JSON Schema conformance.
2. Unique IDs within each namespace.
3. Cross-reference integrity across sources, evidence, assumptions, hypotheses.
4. Minimal semantic invariants that JSON Schema cannot express cleanly.

Usage:
    python tools/validate_uer.py
    python tools/validate_uer.py records/example.uer.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "uer-v0.1.schema.json"
RECORDS_DIR = ROOT / "records"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return sorted(dupes)


def require_refs(
    errors: list[str],
    *,
    record_path: Path,
    owner: str,
    field: str,
    refs: Iterable[str],
    valid_ids: set[str],
) -> None:
    for ref in refs:
        if ref not in valid_ids:
            errors.append(
                f"{record_path}: {owner}.{field} references missing id {ref!r}"
            )


def validate_semantics(record: dict[str, Any], record_path: Path) -> list[str]:
    errors: list[str] = []

    sources = record.get("sources", [])
    evidence = record.get("evidence", [])
    claims = record.get("claims", [])
    assumptions = record.get("assumptions", [])
    hypotheses = record.get("hypotheses", [])
    discriminating = record.get("discriminating_observations", [])

    source_ids = [item["source_id"] for item in sources]
    evidence_ids = [item["evidence_id"] for item in evidence]
    claim_ids = [item["claim_id"] for item in claims]
    assumption_ids = [item["assumption_id"] for item in assumptions]
    hypothesis_ids = [item["hypothesis_id"] for item in hypotheses]
    observation_ids = [item["observation_id"] for item in discriminating]

    namespaces = {
        "source_id": source_ids,
        "evidence_id": evidence_ids,
        "claim_id": claim_ids,
        "assumption_id": assumption_ids,
        "hypothesis_id": hypothesis_ids,
        "observation_id": observation_ids,
    }
    for namespace, values in namespaces.items():
        for duplicate in duplicates(values):
            errors.append(
                f"{record_path}: duplicate {namespace} {duplicate!r}"
            )

    source_set = set(source_ids)
    evidence_set = set(evidence_ids)
    assumption_set = set(assumption_ids)
    hypothesis_set = set(hypothesis_ids)

    for item in evidence:
        owner = item["evidence_id"]
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="source_ids",
            refs=item.get("source_ids", []),
            valid_ids=source_set,
        )

    for item in assumptions:
        owner = item["assumption_id"]
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="source_ids",
            refs=item.get("source_ids", []),
            valid_ids=source_set,
        )

    for item in claims:
        owner = item["claim_id"]
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="supported_by",
            refs=item.get("supported_by", []),
            valid_ids=evidence_set,
        )
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="contradicted_by",
            refs=item.get("contradicted_by", []),
            valid_ids=evidence_set,
        )
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="assumption_ids",
            refs=item.get("assumption_ids", []),
            valid_ids=assumption_set,
        )

        claim_type = item.get("claim_type")
        assumption_refs = item.get("assumption_ids", [])
        if claim_type == "model_dependent" and not assumption_refs:
            errors.append(
                f"{record_path}: {owner} is model_dependent but has no assumption_ids"
            )

        if not item.get("supported_by") and not item.get("contradicted_by"):
            errors.append(
                f"{record_path}: {owner} has neither supporting nor contradicting evidence"
            )

    for item in hypotheses:
        owner = item["hypothesis_id"]
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="supporting_evidence",
            refs=item.get("supporting_evidence", []),
            valid_ids=evidence_set,
        )
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="contradicting_evidence",
            refs=item.get("contradicting_evidence", []),
            valid_ids=evidence_set,
        )

    for item in discriminating:
        owner = item["observation_id"]
        require_refs(
            errors,
            record_path=record_path,
            owner=owner,
            field="discriminates_between",
            refs=item.get("discriminates_between", []),
            valid_ids=hypothesis_set,
        )
        if len(item.get("discriminates_between", [])) < 2:
            errors.append(
                f"{record_path}: {owner} should discriminate between at least two hypotheses"
            )

    # Every evidence object must preserve provenance through at least one source.
    for item in evidence:
        if not item.get("source_ids"):
            errors.append(
                f"{record_path}: {item['evidence_id']} has no provenance source_ids"
            )

    return errors


def validate_record(
    record_path: Path,
    schema_validator: Draft202012Validator,
) -> list[str]:
    errors: list[str] = []
    try:
        record = load_json(record_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{record_path}: invalid JSON: {exc}"]

    schema_errors = sorted(
        schema_validator.iter_errors(record),
        key=lambda err: list(err.absolute_path),
    )
    for err in schema_errors:
        location = ".".join(str(part) for part in err.absolute_path) or "<root>"
        errors.append(f"{record_path}: schema error at {location}: {err.message}")

    if not schema_errors:
        errors.extend(validate_semantics(record, record_path))

    return errors


def resolve_record_paths(args: list[str]) -> list[Path]:
    if args:
        return [Path(arg).resolve() for arg in args]
    return sorted(RECORDS_DIR.glob("*.uer.json"))


def main(argv: list[str]) -> int:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    record_paths = resolve_record_paths(argv)
    if not record_paths:
        print("ERROR: no *.uer.json records found", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    for path in record_paths:
        all_errors.extend(validate_record(path, validator))

    if all_errors:
        print("UER validation failed:", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"UER validation passed for {len(record_paths)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
