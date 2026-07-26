from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from vajra_space.reproduction import (
    build_container_command,
    run_reproduction,
    validate_reproduction_manifest,
    verify_attestation_hmac,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/reproduction.schema.json"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_manifest(workspace: Path, *, output_hash: str | None, input_hash: str | None = None) -> Path:
    input_path = workspace / "input.txt"
    if input_hash is None:
        input_hash = sha256(input_path.read_bytes())
    manifest = {
        "manifest_id": "reproduction:test:local",
        "version": 1,
        "description": "Deterministic local reproduction fixture.",
        "execution_mode": "local",
        "working_directory": ".",
        "timeout_seconds": 10,
        "command": [
            sys.executable,
            "-c",
            "from pathlib import Path; Path('output.txt').write_bytes(b'result\\n')",
        ],
        "expected_exit_code": 0,
        "environment": {"PYTHONHASHSEED": "0"},
        "inputs": [{"path": "input.txt", "sha256": input_hash}],
        "outputs": [{"path": "output.txt", "required": True, "sha256": output_hash}],
        "metadata": {"fixture": True},
    }
    path = workspace / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "input.txt").write_bytes(b"input\n")
    return workspace


def test_success_requires_matching_exit_and_output_hash(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    manifest = write_manifest(workspace, output_hash=sha256(b"result\n"))

    result = run_reproduction(manifest, SCHEMA, workspace, allow_execution=True)

    assert result.status == "success"
    assert result.attestation["observed_exit_code"] == 0
    assert result.attestation["observed_outputs"][0]["sha256"] == sha256(b"result\n")


def test_execution_is_blocked_without_explicit_authorization(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    manifest = write_manifest(workspace, output_hash=sha256(b"result\n"))

    result = run_reproduction(manifest, SCHEMA, workspace)

    assert result.status == "blocked"
    assert any(issue["code"] == "execution_not_authorized" for issue in result.attestation["issues"])
    assert not (workspace / "output.txt").exists()


def test_input_hash_mismatch_blocks_execution(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    manifest = write_manifest(workspace, output_hash=sha256(b"result\n"), input_hash="f" * 64)

    result = run_reproduction(manifest, SCHEMA, workspace, allow_execution=True)

    assert result.status == "blocked"
    assert any(issue["code"] == "input_hash_mismatch" for issue in result.attestation["issues"])
    assert not (workspace / "output.txt").exists()


def test_missing_expected_hash_produces_partial_result(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    manifest = write_manifest(workspace, output_hash=None)

    result = run_reproduction(manifest, SCHEMA, workspace, allow_execution=True)

    assert result.status == "partial"
    assert any(issue["code"] == "output_hash_not_declared" for issue in result.attestation["issues"])


def test_wrong_output_hash_produces_mismatch(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    manifest = write_manifest(workspace, output_hash="a" * 64)

    result = run_reproduction(manifest, SCHEMA, workspace, allow_execution=True)

    assert result.status == "mismatch"
    assert any(issue["code"] == "output_hash_mismatch" for issue in result.attestation["issues"])


def test_preexisting_output_blocks_reproduction(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    (workspace / "output.txt").write_bytes(b"old\n")
    manifest = write_manifest(workspace, output_hash=sha256(b"result\n"))

    result = run_reproduction(manifest, SCHEMA, workspace, allow_execution=True)

    assert result.status == "blocked"
    assert any(issue["code"] == "preexisting_output" for issue in result.attestation["issues"])


def test_hmac_authentication_detects_tampering(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    manifest = write_manifest(workspace, output_hash=sha256(b"result\n"))
    key = b"test-secret-key"

    result = run_reproduction(
        manifest,
        SCHEMA,
        workspace,
        allow_execution=True,
        signing_key=key,
        key_id="test-key",
    )

    assert verify_attestation_hmac(result.attestation, key)
    result.attestation["status"] = "mismatch"
    assert not verify_attestation_hmac(result.attestation, key)


def test_container_command_enforces_baseline_isolation(tmp_path: Path) -> None:
    manifest = {
        "execution_mode": "container",
        "working_directory": "case",
        "environment": {"SEED": "1"},
        "container": {
            "image": "example.invalid/vajra@sha256:" + "1" * 64,
            "user": "65534:65534",
        },
        "command": ["python", "run.py"],
    }

    command = build_container_command(manifest, tmp_path)

    assert command[:3] == ["docker", "run", "--rm"]
    assert ["--network", "none"] == command[3:5]
    assert "--read-only" in command
    assert "--cap-drop" in command
    assert "ALL" in command
    assert "no-new-privileges" in command
    assert manifest["container"]["image"] in command


def test_schema_rejects_container_without_digest() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    manifest = {
        "manifest_id": "reproduction:bad-container",
        "version": 1,
        "execution_mode": "container",
        "working_directory": ".",
        "timeout_seconds": 10,
        "command": ["true"],
        "expected_exit_code": 0,
        "container": {"image": "python:3.12"},
        "inputs": [],
        "outputs": [{"path": "output.txt", "required": True, "sha256": "0" * 64}],
    }

    issues = validate_reproduction_manifest(manifest, schema)

    assert issues
    assert any(issue["path"] == "$.container.image" for issue in issues)
