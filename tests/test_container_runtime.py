from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from vajra_space.container_runtime import build_oci_command, runtime_name


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"


def load_manifest() -> dict:
    return json.loads((CASE / "m87-ehtim-podman-manifest.json").read_text(encoding="utf-8"))


def test_podman_manifest_is_schema_valid() -> None:
    manifest = load_manifest()
    schema = json.loads((ROOT / "schemas/reproduction.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(manifest)) == []


def test_runtime_is_explicitly_podman() -> None:
    manifest = load_manifest()
    assert runtime_name(manifest) == "podman"


def test_podman_command_enforces_isolation_and_digest() -> None:
    manifest = load_manifest()
    command = build_oci_command(manifest, Path("/tmp/vajra-workspace"))

    assert command[:3] == ["podman", "run", "--rm"]
    assert ["--network", "none"] == command[3:5]
    assert "--read-only" in command
    assert ["--cap-drop", "ALL"] == command[command.index("--cap-drop"):command.index("--cap-drop") + 2]
    assert ["--security-opt", "no-new-privileges"] == command[
        command.index("--security-opt"):command.index("--security-opt") + 2
    ]
    assert manifest["container"]["image"] in command
    assert "@sha256:" in manifest["container"]["image"]


def test_podman_manifest_requires_known_docker_output_hash() -> None:
    manifest = load_manifest()
    assert manifest["outputs"] == [
        {
            "path": "outputs/SR1_M87_2017_101_podman.fits",
            "required": True,
            "sha256": "70db37ed8661c6354976f071d4911f77f106fc5f99bcdc0d66a8d2a2ffff16ad",
        }
    ]
    assert manifest["metadata"]["expected_canonical_pixel_sha256"] == (
        "432f97dbc5ba73f6dfb54be6a948911f8c3690c2e28f7b690979038c369ac6c2"
    )


def test_runtime_diversity_is_not_mislabeled_as_independent_science() -> None:
    manifest = load_manifest()
    scope = manifest["metadata"]["independence_scope"]
    assert "runtime-diverse" in scope
    assert "not an independent operator" in scope
    assert "not an independent scientific method" in scope
