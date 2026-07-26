from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"


def read(name: str) -> dict:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_persisted_cross_run_report_binds_contract_and_artifact() -> None:
    report = read("m87-cross-run-stability-report.json")
    contract_path = CASE / "m87-cross-run-stability-contract.json"
    schema_path = ROOT / "schemas/image-stability.schema.json"

    assert report["status"] == "pass"
    assert report["contract_id"] == "image-stability:m87:cross-run:v0.1"
    assert report["contract_status"] == "engineering_derived"
    assert report["inputs"]["contract_sha256"] == sha256_file(contract_path)
    assert report["inputs"]["schema_sha256"] == sha256_file(schema_path)
    assert report["workflow"] == {
        "artifact_digest": "sha256:a1789cb268b5c259dace78f8e3297e189960cf4973232f87842fac2f2d438e29",
        "artifact_id": 8636907398,
        "commit": "bd2f85430d2d8fccff176926ef21226037daa4a5",
        "run_id": 30219938594,
        "run_url": "https://github.com/safal207/Vajra-Space-Evidence-Lab/actions/runs/30219938594",
    }


def test_cross_run_report_proves_semantic_not_bitwise_stability() -> None:
    report = read("m87-cross-run-stability-report.json")

    assert report["reference"]["fits_sha256"] != report["candidate"]["fits_sha256"]
    assert report["measurements"]["image"]["pixel_correlation"] > 0.999
    assert report["measurements"]["image"]["relative_l1_difference"] < 0.01
    assert report["measurements"]["image"]["relative_l2_difference"] < 0.01
    assert all(item["passed"] is True for item in report["comparators"])
    assert "not universal bitwise determinism" in " ".join(report["limitations"])


def test_cross_run_morphology_changes_are_small_and_explicit() -> None:
    measurements = read("m87-cross-run-stability-report.json")["measurements"]["morphology"]

    assert measurements["mean_diameter_absolute_delta_microarcseconds"] < 0.1
    assert measurements["mean_fwhm_absolute_delta_microarcseconds"] < 0.1
    assert measurements["fractional_width_absolute_delta"] < 0.002
    assert measurements["circularity_absolute_delta"] < 0.003


def test_cross_run_evidence_is_linked_without_s4_promotion() -> None:
    evidence = read("evidence-paper-derived-morphology-stability.json")
    claim = read("claim-ring-image.json")

    assert evidence["evidence_id"] in claim["evidence_refs"]
    assert evidence["source_hash"] == "a1789cb268b5c259dace78f8e3297e189960cf4973232f87842fac2f2d438e29"
    assert claim["status"] == "supported"
    assert claim["evidence_level"] == "S3"
    assert claim["version"] == 4
    assert "not official EHT code" in evidence["uncertainty"]["description"]


def test_bootstrap_evidence_no_longer_claims_universal_expected_hash() -> None:
    evidence = read("evidence-ehtim-bootstrap-reproduction.json")
    uncertainty = evidence["uncertainty"]["description"]

    assert "not a universal expected output" in uncertainty
    assert "semantic image and morphology comparators" in uncertainty
