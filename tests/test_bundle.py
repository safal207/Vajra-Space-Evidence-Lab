import hashlib
import json
from pathlib import Path

from vajra_space.bundle import validate_bundle_file


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, data: dict) -> str:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_bundle(tmp_path: Path) -> Path:
    instrument = {
        "instrument_id": "instrument:test",
        "name": "Test telescope",
        "instrument_type": "telescope",
        "operator": "Test operator",
        "location": None,
        "calibration_status": "declared",
        "calibration_evidence_refs": [],
    }
    observation = {
        "observation_id": "observation:test",
        "description": "A traceable test observation.",
        "observed_at": "2026-07-25T00:00:00Z",
        "instrument_ref": "instrument:test",
        "source_hash": "1" * 64,
        "data_uri": None,
        "band_or_channel": None,
        "uncertainty": {"description": "Test uncertainty", "value": None, "unit": None},
    }
    claim = {
        "claim_id": "claim:test",
        "claim_text": "A test observation exists.",
        "claim_type": "OBS",
        "status": "not_assessed",
        "evidence_level": "S0",
        "created_at": "2026-07-25T00:00:00Z",
        "version": 1,
        "supersedes": None,
        "evidence_refs": [],
        "assumption_refs": [],
        "alternative_claim_refs": [],
    }

    hashes = {
        "instrument": write_json(tmp_path / "instrument.json", instrument),
        "observation": write_json(tmp_path / "observation.json", observation),
        "claim": write_json(tmp_path / "claim.json", claim),
    }
    bundle = {
        "bundle_id": "bundle:test",
        "status": "incomplete",
        "objects": [
            {"kind": "instrument", "id": "instrument:test", "path": "instrument.json", "sha256": hashes["instrument"]},
            {"kind": "observation", "id": "observation:test", "path": "observation.json", "sha256": hashes["observation"]},
            {"kind": "claim", "id": "claim:test", "path": "claim.json", "sha256": hashes["claim"]},
        ],
        "root_claim_refs": ["claim:test"],
        "missing": [],
    }
    write_json(tmp_path / "bundle.json", bundle)
    return tmp_path / "bundle.json"


def add_falsification_object(
    bundle_path: Path,
    target_input_ref: str = "observation:test",
) -> None:
    base = bundle_path.parent
    claim_path = base / "claim.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["version"] = 2
    claim["falsification_criteria_refs"] = ["falsification:test:v1"]
    claim_hash = write_json(claim_path, claim)

    falsification = {
        "falsification_id": "falsification:test:v1",
        "target_claim_ref": "claim:test",
        "status": "planned",
        "tests": [
            {
                "test_id": "test:falsification:test",
                "question": "Can the target claim be challenged?",
                "observable": "A registered comparison result.",
                "method": "Evaluate a declared input against a registered condition.",
                "required_input_refs": [target_input_ref],
                "missing_prerequisites": [],
                "support_condition": "The result supports the target.",
                "refutation_condition": "The result refutes the target.",
                "inconclusive_condition": "The result is insufficient.",
                "evaluation_status": "not_evaluated",
                "result_evidence_refs": [],
            }
        ],
        "independence_requirements": ["Use an independently controlled evaluation."],
        "limitations": ["This fixture does not establish a scientific result."],
    }
    falsification_hash = write_json(base / "falsification.json", falsification)

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["objects"][2]["sha256"] = claim_hash
    bundle["objects"].append(
        {
            "kind": "falsification",
            "id": "falsification:test:v1",
            "path": "falsification.json",
            "sha256": falsification_hash,
        }
    )
    write_json(bundle_path, bundle)


def test_valid_bundle_passes(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    result = validate_bundle_file(bundle, ROOT / "schemas/bundle.schema.json")
    assert result.valid, result.issues


def test_registered_falsification_graph_passes(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    add_falsification_object(bundle)

    result = validate_bundle_file(bundle, ROOT / "schemas/bundle.schema.json")

    assert result.valid, result.issues


def test_nested_falsification_reference_is_validated(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    add_falsification_object(bundle, target_input_ref="observation:missing")

    result = validate_bundle_file(bundle, ROOT / "schemas/bundle.schema.json")

    assert not result.valid
    assert any(
        issue.code == "dangling_reference"
        and issue.path == "$[falsification:test:v1].tests.0.required_input_refs"
        for issue in result.issues
    )


def test_dangling_reference_fails(tmp_path: Path) -> None:
    bundle_path = make_bundle(tmp_path)
    observation_path = tmp_path / "observation.json"
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    observation["instrument_ref"] = "instrument:missing"
    new_hash = write_json(observation_path, observation)

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["objects"][1]["sha256"] = new_hash
    write_json(bundle_path, bundle)

    result = validate_bundle_file(bundle_path, ROOT / "schemas/bundle.schema.json")
    assert not result.valid
    assert any(issue.code == "dangling_reference" for issue in result.issues)


def test_hash_mismatch_detects_tampering(tmp_path: Path) -> None:
    bundle_path = make_bundle(tmp_path)
    claim_path = tmp_path / "claim.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["claim_text"] = "Tampered claim"
    write_json(claim_path, claim)

    result = validate_bundle_file(bundle_path, ROOT / "schemas/bundle.schema.json")
    assert not result.valid
    assert any(issue.code == "hash_mismatch" for issue in result.issues)


def test_duplicate_id_fails(tmp_path: Path) -> None:
    bundle_path = make_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["objects"].append(dict(bundle["objects"][0]))
    write_json(bundle_path, bundle)

    result = validate_bundle_file(bundle_path, ROOT / "schemas/bundle.schema.json")
    assert not result.valid
    assert any(issue.code == "duplicate_id" for issue in result.issues)


def test_path_escape_fails(tmp_path: Path) -> None:
    bundle_path = make_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["objects"][0]["path"] = "../outside.json"
    write_json(bundle_path, bundle)

    result = validate_bundle_file(bundle_path, ROOT / "schemas/bundle.schema.json")
    assert not result.valid
    assert any(issue.code == "path_escape" for issue in result.issues)
