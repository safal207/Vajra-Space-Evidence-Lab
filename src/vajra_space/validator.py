from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .scoring import calculate_evidence_level


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _json_path(parts: list[Any]) -> str:
    return "$" if not parts else "$." + ".".join(str(part) for part in parts)


def validate_against_schema(instance: dict[str, Any], schema: dict[str, Any]) -> list[ValidationIssue]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        ValidationIssue("schema_error", error.message, _json_path(list(error.absolute_path)))
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    ]


def validate_claim_semantics(claim: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    level = claim.get("evidence_level")
    status = claim.get("status")

    if status == "not_assessed" and level != "S0":
        issues.append(ValidationIssue("unassessed_must_be_s0", "A not_assessed claim must have evidence_level S0.", "$.evidence_level"))
    if status == "superseded" and not claim.get("supersedes"):
        issues.append(ValidationIssue("superseded_requires_reference", "A superseded claim must declare the prior record.", "$.supersedes"))
    if level in {"S2", "S3", "S4", "S5"} and not claim.get("evidence_refs", []):
        issues.append(ValidationIssue("higher_level_requires_evidence", f"Evidence level {level} requires evidence references.", "$.evidence_refs"))
    return issues


def validate_claim_file(claim_path: Path, schema_path: Path) -> ValidationResult:
    claim = _load_json(claim_path)
    issues = validate_against_schema(claim, _load_json(schema_path))
    if not issues:
        issues.extend(validate_claim_semantics(claim))
    return ValidationResult(not issues, tuple(issues))


def validate_evidence_file(evidence_path: Path, schema_path: Path) -> ValidationResult:
    issues = validate_against_schema(_load_json(evidence_path), _load_json(schema_path))
    return ValidationResult(not issues, tuple(issues))


def validate_declared_level(claim: dict[str, Any], assessment_input: dict[str, Any]) -> list[ValidationIssue]:
    calculated = calculate_evidence_level(assessment_input).level
    declared = claim.get("evidence_level")
    if declared == calculated:
        return []
    return [ValidationIssue("declared_level_mismatch", f"Declared level {declared} does not match deterministic level {calculated}.", "$.evidence_level")]
