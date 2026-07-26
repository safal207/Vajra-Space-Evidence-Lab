from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from vajra_space.cli import main
from vajra_space.ledger import append_record
from vajra_space.reports import build_report, encode_report


ROOT = Path(__file__).resolve().parents[1]


def run_cli(monkeypatch, capsys, arguments: list[str]) -> tuple[int, str]:
    monkeypatch.setattr(sys, "argv", ["vajra-space", *arguments])
    code = main()
    return code, capsys.readouterr().out


def valid_claim() -> dict:
    return {
        "claim_id": "claim:report:test",
        "claim_text": "A deterministic report can be emitted.",
        "claim_type": "OBS",
        "status": "not_assessed",
        "evidence_level": "S0",
        "created_at": "2026-07-26T00:00:00Z",
        "version": 1,
        "supersedes": None,
        "evidence_refs": [],
        "assumption_refs": [],
        "alternative_claim_refs": [],
    }


def valid_evidence() -> dict:
    return {
        "evidence_id": "evidence:report:test",
        "evidence_type": "attestation",
        "source_uri": "urn:vajra:report:test",
        "source_hash": "a" * 64,
        "collected_at": "2026-07-26T00:00:00Z",
        "instrument_ref": None,
        "transformation_refs": [],
        "uncertainty": {
            "description": "Test fixture.",
            "value": None,
            "unit": None,
        },
    }


def local_manifest(input_hash: str) -> dict:
    return {
        "manifest_id": "reproduction:report:test",
        "version": 1,
        "description": "Structured reproduction report fixture.",
        "execution_mode": "local",
        "working_directory": ".",
        "timeout_seconds": 10,
        "command": [sys.executable, "-c", "print('not executed')"],
        "expected_exit_code": 0,
        "environment": {"PYTHONHASHSEED": "0"},
        "inputs": [{"path": "input.txt", "sha256": input_hash}],
        "outputs": [{"path": "output.txt", "required": True, "sha256": None}],
        "metadata": {"fixture": True},
    }


def test_report_encoding_is_deterministic_and_sorts_issues(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text('{"value":1}\n', encoding="utf-8")
    issues = [
        {"code": "z", "path": "$.b", "message": "second"},
        {"code": "a", "path": "$.a", "message": "first"},
    ]

    first = build_report(
        command="validate-test",
        input_path=input_path,
        status="invalid",
        issues=issues,
    )
    second = build_report(
        command="validate-test",
        input_path=input_path,
        status="invalid",
        issues=reversed(issues),
    )

    assert encode_report(first) == encode_report(second)
    assert first["report_version"] == 1
    assert first["issues"] == [
        {"code": "a", "path": "$.a", "message": "first"},
        {"code": "z", "path": "$.b", "message": "second"},
    ]
    assert first["input"]["sha256"] == hashlib.sha256(input_path.read_bytes()).hexdigest()
    assert first["tool"]["name"] == "vajra-space"
    assert first["tool"]["version"] == "0.4.0"


def test_claim_validator_preserves_human_output_and_adds_json(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    claim_path = tmp_path / "claim.json"
    claim_path.write_text(json.dumps(valid_claim()), encoding="utf-8")

    code, output = run_cli(
        monkeypatch,
        capsys,
        ["validate-claim", str(claim_path), "--schema", str(ROOT / "schemas/claim.schema.json")],
    )
    assert code == 0
    assert output == "VALID\n"

    code, output = run_cli(
        monkeypatch,
        capsys,
        [
            "validate-claim",
            str(claim_path),
            "--schema",
            str(ROOT / "schemas/claim.schema.json"),
            "--json",
        ],
    )
    report = json.loads(output)
    assert code == 0
    assert report["status"] == "valid"
    assert report["valid"] is True
    assert report["tool"]["command"] == "validate-claim"
    assert report["issues"] == []


def test_evidence_bundle_ledger_and_manifest_validators_emit_common_envelope(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(valid_evidence()), encoding="utf-8")

    code, output = run_cli(
        monkeypatch,
        capsys,
        [
            "validate-evidence",
            str(evidence_path),
            "--schema",
            str(ROOT / "schemas/evidence.schema.json"),
            "--json",
        ],
    )
    evidence_report = json.loads(output)
    assert code == 0
    assert evidence_report["tool"]["command"] == "validate-evidence"
    assert evidence_report["report_version"] == 1

    bundle_path = ROOT / "cases/m87-black-hole/evidence-bundle.json"
    code, output = run_cli(
        monkeypatch,
        capsys,
        [
            "validate-bundle",
            str(bundle_path),
            "--schema",
            str(ROOT / "schemas/bundle.schema.json"),
            "--json",
        ],
    )
    bundle_report = json.loads(output)
    assert code == 0
    assert bundle_report["tool"]["command"] == "validate-bundle"
    assert bundle_report["status"] == "valid"

    ledger_path = tmp_path / "ledger.json"
    append_record(
        ledger_path,
        {"claim_id": "claim:report:test", "version": 1, "status": "not_assessed"},
        event_type="created",
        actor="test",
    )
    code, output = run_cli(
        monkeypatch,
        capsys,
        ["ledger-validate", str(ledger_path), "--json"],
    )
    ledger_report = json.loads(output)
    assert code == 0
    assert ledger_report["tool"]["command"] == "ledger-validate"
    assert ledger_report["status"] == "valid"

    manifest_path = ROOT / "cases/m87-black-hole/m87-ehtim-podman-manifest.json"
    code, output = run_cli(
        monkeypatch,
        capsys,
        [
            "validate-reproduction-manifest",
            str(manifest_path),
            "--schema",
            str(ROOT / "schemas/reproduction.schema.json"),
            "--json",
        ],
    )
    manifest_report = json.loads(output)
    assert code == 0
    assert manifest_report["tool"]["command"] == "validate-reproduction-manifest"
    assert manifest_report["status"] == "valid"


def test_reproduce_json_wraps_attestation_without_changing_default_output(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    input_path = workspace / "input.txt"
    input_path.write_bytes(b"input\n")
    manifest_path = workspace / "manifest.json"
    manifest_path.write_text(
        json.dumps(local_manifest(hashlib.sha256(input_path.read_bytes()).hexdigest())),
        encoding="utf-8",
    )

    base_arguments = [
        "reproduce",
        str(manifest_path),
        "--schema",
        str(ROOT / "schemas/reproduction.schema.json"),
        "--workspace",
        str(workspace),
    ]

    code, output = run_cli(monkeypatch, capsys, base_arguments)
    direct_attestation = json.loads(output)
    assert code == 4
    assert direct_attestation["status"] == "blocked"
    assert direct_attestation["attestation_version"] == 1
    assert "report_version" not in direct_attestation

    code, output = run_cli(monkeypatch, capsys, [*base_arguments, "--json"])
    report = json.loads(output)
    assert code == 4
    assert report["report_version"] == 1
    assert report["tool"]["command"] == "reproduce"
    assert report["status"] == "blocked"
    assert report["valid"] is False
    assert report["data"]["attestation"]["status"] == "blocked"
    assert report["issues"][0]["code"] == "execution_not_authorized"
