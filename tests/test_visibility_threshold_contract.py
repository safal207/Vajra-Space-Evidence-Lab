from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SCHEMA_PATH = ROOT / "schemas/visibility-threshold-contract.schema.json"
EVALUATION_SCHEMA_PATH = ROOT / "schemas/visibility-threshold-evaluation.schema.json"
CONTRACT_PATH = ROOT / "cases/m87-black-hole/visibility/m87-visibility-threshold-contract.json"
REPORT_PATH = ROOT / "cases/m87-black-hole/visibility/reference.visibility-fit.json"
SCRIPT_PATH = ROOT / "scripts/evaluate_visibility_thresholds.py"


def load_module():
    spec = importlib.util.spec_from_file_location("evaluate_visibility_thresholds", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(schema_path: Path, value: dict) -> list:
    schema = read(schema_path)
    return list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(value)
    )


def reviewed_fixture(*, maximum: float) -> dict:
    contract = deepcopy(read(CONTRACT_PATH))
    contract["contract_id"] = "visibility-threshold:test:reviewed:v1"
    contract["registration_status"] = "reviewed"
    contract["registered_at"] = "2026-07-27T00:00:00Z"
    contract["evaluation_authorized"] = True
    contract["review"] = {
        "status": "approved",
        "reviewer_identity": "reviewer:test:independent",
        "reviewed_at": "2026-07-27T00:05:00Z",
        "review_artifact_ref": "review:test:fixture",
        "independence_statement": "Synthetic unit-test reviewer; not a scientific M87 review.",
    }
    for threshold in contract["thresholds"]:
        threshold["maximum"] = maximum
        threshold["degrees_of_freedom_assumption"] = "Synthetic fixture assumption."
        threshold["uncertainty_model"] = "Synthetic fixture uncertainty model."
        threshold["rationale"] = "Synthetic fixture threshold used only to test evaluator behavior."
        threshold["source_refs"] = ["fixture:unit-test"]
        threshold["preregistered_before_evaluation"] = True
    return contract


def test_threshold_schemas_are_valid() -> None:
    for path in (CONTRACT_SCHEMA_PATH, EVALUATION_SCHEMA_PATH):
        schema = read(path)
        Draft202012Validator.check_schema(schema)


def test_real_m87_threshold_contract_is_valid_but_not_authorized() -> None:
    contract = read(CONTRACT_PATH)

    assert validate(CONTRACT_SCHEMA_PATH, contract) == []
    assert contract["registration_status"] == "draft"
    assert contract["evaluation_authorized"] is False
    assert contract["review"]["status"] == "pending"
    assert all(item["maximum"] is None for item in contract["thresholds"])
    assert all(item["preregistered_before_evaluation"] is False for item in contract["thresholds"])


def test_draft_contract_blocks_without_reading_a_scientific_verdict() -> None:
    module = load_module()
    contract = read(CONTRACT_PATH)
    report = read(REPORT_PATH)

    result = module.evaluate(
        contract,
        report,
        contract_sha256="a" * 64,
        report_sha256="b" * 64,
    )

    assert validate(EVALUATION_SCHEMA_PATH, result) == []
    assert result["status"] == "blocked"
    assert result["verdict"] == "not_evaluated"
    assert result["results"] == []
    codes = {item["code"] for item in result["issues"]}
    assert "CONTRACT_NOT_REVIEWED" in codes
    assert "INDEPENDENT_REVIEW_NOT_APPROVED" in codes
    assert "EVALUATION_NOT_AUTHORIZED" in codes
    assert "THRESHOLD_NOT_PREREGISTERED" in codes
    assert "MISSING_MAXIMUM" in codes
    assert "MISSING_DEGREES_OF_FREEDOM_ASSUMPTION" in codes
    assert "MISSING_UNCERTAINTY_MODEL" in codes
    assert "MISSING_THRESHOLD_RATIONALE" in codes
    assert "MISSING_THRESHOLD_SOURCE" in codes


def test_reviewed_synthetic_fixture_can_accept_without_changing_m87_contract() -> None:
    module = load_module()
    contract = reviewed_fixture(maximum=10000.0)
    report = read(REPORT_PATH)

    assert validate(CONTRACT_SCHEMA_PATH, contract) == []
    result = module.evaluate(
        contract,
        report,
        contract_sha256="c" * 64,
        report_sha256="d" * 64,
    )

    assert validate(EVALUATION_SCHEMA_PATH, result) == []
    assert result["status"] == "complete"
    assert result["verdict"] == "accept"
    assert len(result["results"]) == 8
    assert all(item["outcome"] == "pass" for item in result["results"])


def test_reviewed_synthetic_fixture_rejects_when_one_bound_fails() -> None:
    module = load_module()
    contract = reviewed_fixture(maximum=10000.0)
    target = next(
        threshold
        for threshold in contract["thresholds"]
        if threshold["band_id"] == "low" and threshold["observable"] == "cphase"
    )
    target["maximum"] = 1.0
    report = read(REPORT_PATH)

    result = module.evaluate(
        contract,
        report,
        contract_sha256="e" * 64,
        report_sha256="f" * 64,
    )

    assert validate(EVALUATION_SCHEMA_PATH, result) == []
    assert result["status"] == "complete"
    assert result["verdict"] == "reject"
    failed = [item for item in result["results"] if item["outcome"] == "fail"]
    assert [item["threshold_id"] for item in failed] == ["threshold:m87:low:cphase:v0.1"]


def test_threshold_evaluator_is_python_syntax_valid() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    compile(source, str(SCRIPT_PATH), "exec")
    assert "CONTRACT_NOT_REVIEWED" in source
    assert "INDEPENDENT_REVIEW_NOT_APPROVED" in source
    assert '"status": "blocked"' in source
