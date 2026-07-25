from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "m87-black-hole"
PINNED_COMMIT = "27ae76aacb9067a83388395c3826012b97aac371"


def load(name: str) -> dict:
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_release_manifest_is_internally_consistent() -> None:
    manifest = load("source-release-manifest.json")
    objects = manifest["objects"]

    assert manifest["source_commit"] == PINNED_COMMIT
    assert manifest["object_count"] == len(objects) == 34
    assert len({item["path"] for item in objects}) == len(objects)
    assert all(item["size_bytes"] > 0 for item in objects)
    assert all(item["sha256"] != "0" * 64 for item in objects)

    tree_hasher = hashlib.sha256()
    for item in objects:
        tree_hasher.update(
            f"{item['sha256']} {item['size_bytes']} {item['path']}\n".encode("utf-8")
        )
    assert tree_hasher.hexdigest() == manifest["release_tree_sha256"]

    uvfits = [item for item in objects if item["path"].endswith(".uvfits")]
    assert len(uvfits) == 8


def test_release_hash_is_bound_to_evidence_observation_and_claim() -> None:
    manifest = load("source-release-manifest.json")
    evidence = load("evidence-calibrated-release.json")
    observation = load("observation.json")
    claim = load("claim-compact-radio-source.json")

    release_hash = manifest["release_tree_sha256"]
    assert evidence["source_hash"] == release_hash
    assert observation["source_hash"] == release_hash
    assert evidence["evidence_id"] in claim["evidence_refs"]
    assert PINNED_COMMIT in evidence["source_uri"]
    assert PINNED_COMMIT in observation["data_uri"]
