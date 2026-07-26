from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def issue(code: str, message: str, threshold_id: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "threshold_id": threshold_id,
    }


def authority_issues(contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    registration_status = contract.get("registration_status")
    review_status = contract.get("review", {}).get("status")

    if registration_status != "reviewed":
        issues.append(issue(
            "CONTRACT_NOT_REVIEWED",
            f"Threshold contract registration_status is {registration_status!r}, not 'reviewed'.",
        ))
    if review_status != "approved":
        issues.append(issue(
            "INDEPENDENT_REVIEW_NOT_APPROVED",
            f"Threshold contract review status is {review_status!r}, not 'approved'.",
        ))
    if contract.get("evaluation_authorized") is not True:
        issues.append(issue(
            "EVALUATION_NOT_AUTHORIZED",
            "Threshold contract does not authorize evaluation.",
        ))

    for threshold in contract.get("thresholds", []):
        threshold_id = threshold.get("threshold_id")
        comparison = threshold.get("comparison")
        minimum = threshold.get("minimum")
        maximum = threshold.get("maximum")
        if threshold.get("preregistered_before_evaluation") is not True:
            issues.append(issue(
                "THRESHOLD_NOT_PREREGISTERED",
                "Threshold is not marked as preregistered before evaluation.",
                threshold_id,
            ))
        if comparison == "maximum" and maximum is None:
            issues.append(issue("MISSING_MAXIMUM", "Maximum threshold is missing.", threshold_id))
        elif comparison == "minimum" and minimum is None:
            issues.append(issue("MISSING_MINIMUM", "Minimum threshold is missing.", threshold_id))
        elif comparison == "interval" and (minimum is None or maximum is None):
            issues.append(issue("MISSING_INTERVAL_BOUND", "Interval threshold requires both bounds.", threshold_id))
        if threshold.get("degrees_of_freedom_assumption") is None:
            issues.append(issue(
                "MISSING_DEGREES_OF_FREEDOM_ASSUMPTION",
                "Degrees-of-freedom assumption is not declared.",
                threshold_id,
            ))
        if threshold.get("uncertainty_model") is None:
            issues.append(issue(
                "MISSING_UNCERTAINTY_MODEL",
                "Uncertainty model is not declared.",
                threshold_id,
            ))
        if threshold.get("rationale") is None:
            issues.append(issue(
                "MISSING_THRESHOLD_RATIONALE",
                "Scientific rationale is not declared.",
                threshold_id,
            ))
        if not threshold.get("source_refs"):
            issues.append(issue(
                "MISSING_THRESHOLD_SOURCE",
                "Threshold has no source or review reference.",
                threshold_id,
            ))

    return issues


def observation_index(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for band in report.get("bands", []):
        band_id = band.get("band_id")
        for observable in band.get("observables", []):
            name = observable.get("observable")
            if isinstance(band_id, str) and isinstance(name, str):
                index[(band_id, name)] = observable
    return index


def passes_threshold(value: float, comparison: str, minimum: float | None, maximum: float | None) -> bool:
    if comparison == "maximum":
        return maximum is not None and value <= maximum
    if comparison == "minimum":
        return minimum is not None and value >= minimum
    if comparison == "interval":
        return minimum is not None and maximum is not None and minimum <= value <= maximum
    return False


def evaluate(
    contract: dict[str, Any],
    report: dict[str, Any],
    *,
    contract_sha256: str,
    report_sha256: str,
) -> dict[str, Any]:
    authority = {
        "registration_status": str(contract.get("registration_status", "unknown")),
        "review_status": str(contract.get("review", {}).get("status", "unknown")),
        "evaluation_authorized": contract.get("evaluation_authorized") is True,
    }
    blocking = authority_issues(contract)

    method = report.get("method", {})
    binding = contract.get("method_binding", {})
    if method.get("method_id") != binding.get("method_id"):
        blocking.append(issue(
            "METHOD_BINDING_MISMATCH",
            "Report method_id does not match the threshold contract binding.",
        ))
    if method.get("library") != binding.get("library"):
        blocking.append(issue(
            "LIBRARY_BINDING_MISMATCH",
            "Report library does not match the threshold contract binding.",
        ))
    if method.get("declared_version") != binding.get("declared_version"):
        blocking.append(issue(
            "VERSION_BINDING_MISMATCH",
            "Report library version does not match the threshold contract binding.",
        ))

    if blocking:
        return {
            "evaluation_version": 1,
            "status": "blocked",
            "verdict": "not_evaluated",
            "contract_id": contract["contract_id"],
            "contract_sha256": contract_sha256,
            "report_sha256": report_sha256,
            "authority": authority,
            "results": [],
            "issues": blocking,
        }

    observations = observation_index(report)
    results: list[dict[str, Any]] = []
    evaluation_issues: list[dict[str, Any]] = []

    for threshold in contract["thresholds"]:
        key = (threshold["band_id"], threshold["observable"])
        observed = observations.get(key)
        if observed is None or observed.get("status") != "success":
            results.append({
                "threshold_id": threshold["threshold_id"],
                "band_id": threshold["band_id"],
                "observable": threshold["observable"],
                "observed_value": None,
                "comparison": threshold["comparison"],
                "minimum": threshold["minimum"],
                "maximum": threshold["maximum"],
                "outcome": "missing_observation",
            })
            evaluation_issues.append(issue(
                "MISSING_SUCCESSFUL_OBSERVATION",
                "No successful observation matches this registered threshold.",
                threshold["threshold_id"],
            ))
            continue

        value = float(observed["reduced_chi_squared"])
        passed = passes_threshold(
            value,
            threshold["comparison"],
            threshold["minimum"],
            threshold["maximum"],
        )
        results.append({
            "threshold_id": threshold["threshold_id"],
            "band_id": threshold["band_id"],
            "observable": threshold["observable"],
            "observed_value": value,
            "comparison": threshold["comparison"],
            "minimum": threshold["minimum"],
            "maximum": threshold["maximum"],
            "outcome": "pass" if passed else "fail",
        })

    if any(result["outcome"] == "missing_observation" for result in results):
        status = "partial"
        verdict = "inconclusive"
    elif any(result["outcome"] == "fail" for result in results):
        status = "complete"
        verdict = "reject"
    else:
        status = "complete"
        verdict = "accept"

    return {
        "evaluation_version": 1,
        "status": status,
        "verdict": verdict,
        "contract_id": contract["contract_id"],
        "contract_sha256": contract_sha256,
        "report_sha256": report_sha256,
        "authority": authority,
        "results": results,
        "issues": evaluation_issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = evaluate(
        contract,
        report,
        contract_sha256=sha256_file(args.contract),
        report_sha256=sha256_file(args.report),
    )
    encoded = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["status"] in {"blocked", "complete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
