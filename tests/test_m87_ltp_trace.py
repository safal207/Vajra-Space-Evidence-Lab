from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VISIBILITY = ROOT / "cases/m87-black-hole/visibility"
TRACE = ROOT / "cases/m87-black-hole/ltp/m87-visibility-audit.jsonl"


def normalize_javascript_numbers(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_javascript_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_javascript_numbers(item) for key, item in value.items()}
    return value


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        normalize_javascript_numbers(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def test_visibility_source_manifest_matches_committed_reports() -> None:
    manifest = json.loads(
        (VISIBILITY / "source-artifact-manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["workflow"]["run_id"] == 30221599082
    assert manifest["workflow"]["head_sha"] == "b183c73a9270f87b8f1cba48ae864ee53cdfe9b2"
    assert manifest["artifact"]["digest"] == (
        "sha256:4c3ffa2d2424227df4264615e9e9b8a506a9ffec9e0b4d836a601faf6f5861be"
    )

    for registered in manifest["files"]:
        path = VISIBILITY / registered["path"]
        assert path.is_file()
        assert path.stat().st_size == registered["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == registered["sha256"]


def test_visibility_reports_preserve_threshold_boundary() -> None:
    cross_run = json.loads(
        (VISIBILITY / "m87-visibility-cross-run.json").read_text(encoding="utf-8")
    )
    reference = json.loads(
        (VISIBILITY / "reference.visibility-fit.json").read_text(encoding="utf-8")
    )
    candidate = json.loads(
        (VISIBILITY / "candidate.visibility-fit.json").read_text(encoding="utf-8")
    )

    assert cross_run["status"] == "diagnostic_complete"
    assert cross_run["interpretation_status"] == "thresholds_not_registered"
    assert cross_run["common_successful_observables"] == 8
    assert reference["summary"] == {
        "failed_count": 0,
        "requested_count": 8,
        "successful_count": 8,
    }
    assert candidate["summary"] == reference["summary"]


def test_ltp_trace_is_canonical_hash_chained_jsonl() -> None:
    lines = [line for line in TRACE.read_text(encoding="utf-8").splitlines() if line]
    entries = [json.loads(line) for line in lines]

    assert len(entries) == 5
    assert [entry["i"] for entry in entries] == list(range(5))
    assert len({entry["session_id"] for entry in entries}) == 1

    previous = "0" * 64
    for entry in entries:
        assert entry["prev_hash"] == previous
        expected = hashlib.sha256(
            previous.encode("utf-8") + canonical_json_bytes(entry["frame"])
        ).hexdigest()
        assert entry["hash"] == expected
        assert entry["frame"]["v"] == "0.1"
        previous = entry["hash"]


def test_ltp_route_allows_facts_and_blocks_overclaims() -> None:
    entries = [
        json.loads(line)
        for line in TRACE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    route = next(
        entry["frame"]
        for entry in entries
        if entry["frame"]["type"] == "route_response"
    )
    branches = route["payload"]["branches"]

    assert [branch["id"] for branch in branches] == [
        "A-observed-diagnostics",
        "B-absolute-fit-threshold",
        "C-refute-alternatives",
    ]
    assert branches[0]["status"] == "admissible"
    assert all(branch["status"] == "blocked" for branch in branches[1:])
    assert "thresholds_not_registered" in branches[1]["constraints"]
    assert "falsification_tests_not_evaluated" in branches[2]["constraints"]
