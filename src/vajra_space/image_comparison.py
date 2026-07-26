from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


COMPARISON_STATUSES = ("pass", "mismatch", "incomplete", "invalid_contract")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metric_value(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def validate_comparison_contract(
    contract: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, str]]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues: list[dict[str, str]] = []
    for error in sorted(
        validator.iter_errors(contract),
        key=lambda item: list(item.absolute_path),
    ):
        path = "$" if not error.absolute_path else "$.​" + ".".join(
            str(part) for part in error.absolute_path
        )
        issues.append({
            "code": "schema_error",
            "path": path.replace("$.​", "$.") ,
            "message": error.message,
        })
    return issues


def _evaluate(value: float, comparator: dict[str, Any]) -> bool:
    operator = comparator["operator"]
    if operator == "range":
        return comparator["minimum"] <= value <= comparator["maximum"]
    if operator == "max":
        return value <= comparator["maximum"]
    if operator == "min":
        return value >= comparator["minimum"]
    raise ValueError(f"Unsupported comparison operator: {operator}")


def compare_features(
    feature_report: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    missing_required = False
    required_mismatch = False

    for comparator in sorted(
        contract["comparators"],
        key=lambda item: item["comparator_id"],
    ):
        try:
            raw_value = _metric_value(feature_report, comparator["metric_path"])
        except KeyError:
            raw_value = None

        if raw_value is None:
            passed: bool | None = None
            state = "missing"
            if comparator["required"]:
                missing_required = True
        else:
            value = float(raw_value)
            passed = _evaluate(value, comparator)
            state = "pass" if passed else "mismatch"
            if comparator["required"] and not passed:
                required_mismatch = True

        results.append({
            "comparator_id": comparator["comparator_id"],
            "metric_path": comparator["metric_path"],
            "operator": comparator["operator"],
            "minimum": comparator.get("minimum"),
            "maximum": comparator.get("maximum"),
            "required": comparator["required"],
            "observed": raw_value,
            "passed": passed,
            "state": state,
            "provenance": comparator["provenance"],
            "interpretation": comparator["interpretation"],
        })

    if missing_required:
        status = "incomplete"
    elif required_mismatch:
        status = "mismatch"
    else:
        status = "pass"

    return {
        "report_version": 1,
        "status": status,
        "contract_id": contract["contract_id"],
        "contract_version": contract["version"],
        "contract_status": contract["status"],
        "claim_ref": contract["claim_ref"],
        "feature_method_id": feature_report.get("method", {}).get("method_id"),
        "comparators": results,
        "limitations": contract["limitations"],
    }


def compare_feature_files(
    feature_path: Path,
    contract_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    feature_report = json.loads(feature_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    contract_issues = validate_comparison_contract(contract, schema)
    if contract_issues:
        return {
            "report_version": 1,
            "status": "invalid_contract",
            "contract_id": contract.get("contract_id"),
            "feature_report": {
                "path": str(feature_path),
                "sha256": sha256_file(feature_path),
            },
            "contract": {
                "path": str(contract_path),
                "sha256": sha256_file(contract_path),
            },
            "issues": contract_issues,
        }

    report = compare_features(feature_report, contract)
    report["feature_report"] = {
        "path": str(feature_path),
        "sha256": sha256_file(feature_path),
    }
    report["contract"] = {
        "path": str(contract_path),
        "sha256": sha256_file(contract_path),
    }
    report["issues"] = []
    return report
