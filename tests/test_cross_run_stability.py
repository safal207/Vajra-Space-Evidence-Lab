from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "cases/m87-black-hole/m87-cross-run-stability-contract.json"
SCHEMA = ROOT / "schemas/image-stability.schema.json"
SCRIPT = ROOT / "scripts/compare_m87_cross_run_stability.py"


def test_cross_run_stability_contract_is_schema_valid() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(contract)
    )
    assert errors == []


def test_contract_records_distinct_exact_outputs_and_same_environment() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    reference = contract["reference"]
    candidate = contract["candidate"]

    assert reference["fits_sha256"] != candidate["fits_sha256"]
    assert reference["canonical_pixel_sha256"] != candidate["canonical_pixel_sha256"]
    assert reference["oci_reference"] == candidate["oci_reference"]
    assert reference["workflow_run_id"] != candidate["workflow_run_id"]
    assert contract["status"] == "engineering_derived"


def test_contract_requires_pixel_and_morphology_stability() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    comparators = {item["comparator_id"]: item for item in contract["comparators"]}

    assert comparators["pixel-correlation"] == {
        "basis": "A correlation above 0.999 requires the reconstructed image morphology to remain nearly identical despite byte-level drift.",
        "comparator_id": "pixel-correlation",
        "metric_path": "image.pixel_correlation",
        "operator": "min",
        "threshold": 0.999,
    }
    assert comparators["relative-l2-difference"]["threshold"] == 0.02
    assert comparators["diameter-absolute-delta"]["threshold"] == 1.0
    assert comparators["fractional-width-absolute-delta"]["threshold"] == 0.02
    assert comparators["circularity-absolute-delta"]["threshold"] == 0.02


def test_contract_does_not_claim_universal_determinism_or_s4() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    limitations = " ".join(contract["limitations"])

    assert "not universal bitwise determinism" in limitations
    assert "cannot promote" in limitations
    assert "engineering-derived" in limitations


def test_cross_run_comparator_script_is_syntax_valid() -> None:
    compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")
