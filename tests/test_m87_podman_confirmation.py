from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"


def read(name: str) -> dict:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_podman_result_matches_executable_manifest() -> None:
    manifest = read("m87-ehtim-podman-manifest.json")
    result = read("m87-ehtim-podman-confirmation.json")

    assert result["status"] == "runtime_diverse_exact_match"
    assert result["environment"]["manifest_id"] == manifest["manifest_id"]
    assert result["environment"]["oci_reference"] == manifest["container"]["image"]
    assert result["environment"]["confirmation_runtime"] == manifest["container"]["runtime"]
    assert result["output"]["fits_sha256"] == manifest["outputs"][0]["sha256"]
    assert result["output"]["canonical_pixel_sha256"] == manifest["metadata"]["expected_canonical_pixel_sha256"]
    assert result["output"]["matches_prior_docker_fits"] is True
    assert result["output"]["matches_prior_docker_pixels"] is True


def test_podman_result_records_isolation_conformance() -> None:
    result = read("m87-ehtim-podman-confirmation.json")
    assert result["runtime_conformance"] == {
        "declared_persistent_workspace_writable": True,
        "effective_capabilities_zero": True,
        "network_disabled": True,
        "root_filesystem_read_only": True,
        "timeout_terminated_execution": True,
    }


def test_podman_evidence_is_linked_without_overpromotion() -> None:
    claim = read("claim-ring-image.json")
    evidence = read("evidence-ehtim-podman-runtime-confirmation.json")

    assert evidence["evidence_id"] in claim["evidence_refs"]
    assert claim["claim_type"] == "REC"
    assert claim["status"] == "supported"
    assert claim["evidence_level"] == "S3"
    assert claim["version"] >= 3
    assert "runtime diversity only" in evidence["uncertainty"]["description"]
    assert "not independent" in evidence["uncertainty"]["description"]


def test_runtime_diverse_result_does_not_claim_independent_science() -> None:
    result = read("m87-ehtim-podman-confirmation.json")
    scope = result["independence_scope"]
    assert "not an independent operator" in scope
    assert "independent dataset" in scope
    assert "independent scientific method" in scope
