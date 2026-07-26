from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from vajra_space.bundle import validate_bundle_file


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"
SCHEMA = json.loads(
    (ROOT / "schemas/falsification.schema.json").read_text(encoding="utf-8")
)


MAPPINGS = {
    "claim-alternative-calibration-artifact.json": "falsification-calibration-artifact.json",
    "claim-alternative-imaging-prior.json": "falsification-imaging-prior.json",
    "claim-alternative-jet-only.json": "falsification-jet-only.json",
    "claim-alternative-non-kerr.json": "falsification-non-kerr.json",
    "claim-alternative-variability-bias.json": "falsification-variability-bias.json",
}


def read(name: str) -> dict:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_every_registered_falsification_object_is_schema_valid() -> None:
    for filename in MAPPINGS.values():
        value = read(filename)
        errors = list(
            Draft202012Validator(
                SCHEMA,
                format_checker=FormatChecker(),
            ).iter_errors(value)
        )
        assert errors == [], filename
        assert len(value["tests"]) >= 2
        assert value["independence_requirements"]
        assert value["limitations"]


def test_each_alternative_claim_links_to_its_targeted_criteria() -> None:
    for claim_filename, criteria_filename in MAPPINGS.items():
        claim = read(claim_filename)
        criteria = read(criteria_filename)

        assert claim["version"] == 2
        assert claim["claim_type"] == "SPEC"
        assert claim["evidence_level"] == "S0"
        assert claim["falsification_criteria_refs"] == [criteria["falsification_id"]]
        assert criteria["target_claim_ref"] == claim["claim_id"]


def test_criteria_encode_support_refutation_and_inconclusive_states() -> None:
    for filename in MAPPINGS.values():
        criteria = read(filename)
        for test in criteria["tests"]:
            assert test["question"]
            assert test["observable"]
            assert test["method"]
            assert test["support_condition"]
            assert test["refutation_condition"]
            assert test["inconclusive_condition"]
            assert test["evaluation_status"] in {"not_evaluated", "pending_data"}
            assert isinstance(test["required_input_refs"], list)
            assert isinstance(test["result_evidence_refs"], list)


def test_bundle_recursively_validates_nested_criteria_references() -> None:
    result = validate_bundle_file(
        CASE / "evidence-bundle.json",
        ROOT / "schemas/bundle.schema.json",
    )
    assert result.valid
    assert result.issues == ()


def test_falsification_requirement_is_removed_but_evaluations_remain_open() -> None:
    bundle = read("evidence-bundle.json")
    missing = set(bundle["missing"])

    assert "machine-readable falsification criteria" not in missing
    assert "materially independent confirmation objects" in missing

    imaging = read("falsification-imaging-prior.json")
    assert imaging["status"] == "partially_evaluable"
    statuses = {test["evaluation_status"] for test in imaging["tests"]}
    assert statuses == {"pending_data", "not_evaluated"}
