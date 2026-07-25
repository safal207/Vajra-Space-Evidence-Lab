import json
from pathlib import Path

from jsonschema import Draft202012Validator

from vajra_space.ledger import append_record, validate_ledger_file
from vajra_space.scoring import calculate_evidence_level


ROOT = Path(__file__).resolve().parents[1]


def test_s0_fail_closed() -> None:
    assert calculate_evidence_level({"observation_present": True}).level == "S0"


def test_s3_requires_reproduction_contract() -> None:
    assessment = calculate_evidence_level({
        "provenance_complete": True,
        "observation_present": True,
        "data_available": True,
        "method_available": True,
        "code_available": True,
        "environment_pinned": True,
        "uncertainty_declared": True,
        "reproduced": True,
    })
    assert assessment.level == "S3"


def test_ledger_detects_tampering(tmp_path: Path) -> None:
    claim = {"claim_id": "claim:test", "version": 1, "status": "not_assessed"}
    ledger = tmp_path / "ledger.json"
    append_record(ledger, claim, event_type="created", actor="tester")
    records = json.loads(ledger.read_text(encoding="utf-8"))
    records[0]["actor"] = "attacker"
    ledger.write_text(json.dumps(records), encoding="utf-8")
    assert not validate_ledger_file(ledger).valid


def test_all_schemas_are_valid_metaschemas() -> None:
    for path in (ROOT / "schemas").glob("*.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
