from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"


def objects_by_path(manifest: dict) -> dict[str, dict]:
    return {item["path"]: item for item in manifest["objects"]}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_m87_reproduction_plan_binds_exact_data_and_pipeline_hashes() -> None:
    plan = json.loads((CASE / "eht-imaging-reproduction-plan.json").read_text(encoding="utf-8"))
    data_manifest = json.loads((CASE / "source-release-manifest.json").read_text(encoding="utf-8"))
    imaging_manifest = json.loads((CASE / "imaging-source-release-manifest.json").read_text(encoding="utf-8"))

    data_objects = objects_by_path(data_manifest)
    imaging_objects = objects_by_path(imaging_manifest)

    assert plan["status"] == "blocked"
    assert plan["source_releases"]["data"]["commit"] == data_manifest["source_commit"]
    assert plan["source_releases"]["data"]["tree_sha256"] == data_manifest["release_tree_sha256"]
    assert plan["source_releases"]["imaging"]["commit"] == imaging_manifest["source_commit"]
    assert plan["source_releases"]["imaging"]["tree_sha256"] == imaging_manifest["release_tree_sha256"]

    bound_inputs = {item["role"]: item for item in plan["inputs"]}
    assert bound_inputs["low_band_uvfits"]["sha256"] == data_objects[
        "uvfits/SR1_M87_2017_101_lo_hops_netcal_StokesI.uvfits"
    ]["sha256"]
    assert bound_inputs["high_band_uvfits"]["sha256"] == data_objects[
        "uvfits/SR1_M87_2017_101_hi_hops_netcal_StokesI.uvfits"
    ]["sha256"]
    assert bound_inputs["pipeline_code"]["sha256"] == imaging_objects[
        "eht-imaging/eht-imaging_pipeline.py"
    ]["sha256"]


def test_m87_plan_binds_verified_oci_environment_and_exact_lock() -> None:
    plan = json.loads((CASE / "eht-imaging-reproduction-plan.json").read_text(encoding="utf-8"))
    provenance = json.loads((CASE / "m87-ehtim-environment-provenance.json").read_text(encoding="utf-8"))
    environment = plan["environment"]

    assert environment["oci_reference"] == provenance["oci_reference"]
    assert environment["base_reference"] == provenance["base_reference"]
    assert environment["platform"] == provenance["platform"]
    assert environment["lock_sha256"] == provenance["environment_lock_sha256"]
    assert environment["upstream_ehtim"]["commit"] == provenance["ehtim_commit"]
    assert environment["upstream_ehtim"]["tree_sha256"] == provenance["ehtim_tree_sha256"]
    assert environment["compatibility_patch"]["sha256"] == provenance["compatibility_patch_sha256"]
    assert environment["verification"]["workflow_run_id"] == provenance["workflow_run_id"]

    lock_path = ROOT / environment["lock_path"]
    patch_path = ROOT / environment["compatibility_patch"]["path"]
    assert sha256_file(lock_path) == provenance["environment_lock_sha256"]
    assert sha256_file(patch_path) == provenance["compatibility_patch_sha256"]
    assert provenance["verification"] == {
        "build_and_push": "success",
        "ehtim_version_import": "success",
        "official_pipeline_help": "success",
        "pull_by_digest": "success",
    }


def test_m87_plan_cannot_be_promoted_while_scientific_blockers_remain() -> None:
    plan = json.loads((CASE / "eht-imaging-reproduction-plan.json").read_text(encoding="utf-8"))
    blocker_codes = {item["code"] for item in plan["blockers"]}

    assert "container_digest_missing" not in blocker_codes
    assert blocker_codes == {
        "expected_output_hash_missing",
        "scientific_metrics_missing",
        "randomness_contract_unverified",
    }
    assert plan["expected_outputs"][0]["sha256"] is None
    assert "only after every remaining blocker is resolved" in plan["promotion_rule"]


def test_m87_plan_matches_official_fiducial_script_parameters() -> None:
    plan = json.loads((CASE / "eht-imaging-reproduction-plan.json").read_text(encoding="utf-8"))
    parameters = plan["fiducial_parameters"]

    assert parameters["compact_flux_jy"] == 0.6
    assert parameters["prior_fwhm_microarcseconds"] == 40.0
    assert parameters["fractional_systematic_noise"] == 0.02
    assert parameters["pixels"] == 64
    assert parameters["field_of_view_microarcseconds"] == 128.0
    assert parameters["max_iterations"] == 100
    assert parameters["stopping_criterion"] == 0.0001
    assert parameters["reverse_taper_microarcseconds"] == 5.0
