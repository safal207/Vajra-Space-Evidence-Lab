from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from vajra_space.image_comparison import compare_features


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "cases/m87-black-hole/m87-image-comparison-contract.json"
SCHEMA_PATH = ROOT / "schemas/image-comparison.schema.json"
ANALYZER_PATH = ROOT / "scripts/analyze_m87_eht_features.py"


def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def feature_report(
    diameter: float = 40.5,
    fractional_width: float | None = 0.4,
    circularity: float | None = 0.06,
) -> dict:
    metrics = {
        "mean_diameter_microarcseconds": diameter,
        "fractional_width": fractional_width,
        "circularity_fractional_spread": circularity,
    }
    return {
        "report_version": 1,
        "method": {
            "method_id": "eht-paper-vi-section-7-case-b-derived-v0.1",
        },
        "metrics": metrics,
    }


def test_comparison_contract_is_schema_valid() -> None:
    value = contract()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(value)
    )
    assert errors == []
    assert value["status"] == "paper_derived"
    assert value["claim_ref"] == "claim:m87:ring-image"


def test_paper_derived_comparator_passes_consistent_features() -> None:
    report = compare_features(feature_report(), contract())

    assert report["status"] == "pass"
    assert all(item["passed"] is True for item in report["comparators"])
    assert report["feature_method_id"] == "eht-paper-vi-section-7-case-b-derived-v0.1"


def test_diameter_outside_published_span_is_mismatch() -> None:
    report = compare_features(feature_report(diameter=50.0), contract())

    assert report["status"] == "mismatch"
    diameter = next(
        item for item in report["comparators"]
        if item["comparator_id"] == "m87-ring-diameter-paper-vi"
    )
    assert diameter["passed"] is False
    assert diameter["observed"] == 50.0


def test_missing_required_metric_is_incomplete_not_pass() -> None:
    report = compare_features(
        feature_report(fractional_width=None),
        contract(),
    )

    assert report["status"] == "incomplete"
    width = next(
        item for item in report["comparators"]
        if item["comparator_id"] == "m87-fractional-width-paper-vi"
    )
    assert width["state"] == "missing"
    assert width["passed"] is None


def test_contract_does_not_claim_official_eht_code_or_s4() -> None:
    value = contract()
    limitations = " ".join(value["limitations"])

    assert "not the original EHT" in limitations
    assert "does not establish the Kerr" in limitations
    assert value["status"] != "independently_reviewed"


def test_scientific_analyzer_is_python_syntax_valid() -> None:
    source = ANALYZER_PATH.read_text(encoding="utf-8")
    compile(source, str(ANALYZER_PATH), "exec")
