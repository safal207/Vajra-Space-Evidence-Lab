from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


STATUSES = ("success", "partial", "mismatch", "blocked")


@dataclass(frozen=True)
class ReproductionResult:
    status: str
    attestation: dict[str, Any]


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_inside(base: Path, relative: str) -> Path:
    candidate_path = Path(relative)
    if candidate_path.is_absolute():
        raise ValueError(f"Absolute paths are forbidden: {relative}")
    candidate = (base / candidate_path).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace: {relative}") from exc
    return candidate


def validate_reproduction_manifest(
    manifest: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, str]]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues: list[dict[str, str]] = []
    for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.absolute_path)):
        path = "$" if not error.absolute_path else "$." + ".".join(str(part) for part in error.absolute_path)
        issues.append({"code": "schema_error", "path": path, "message": error.message})
    return issues


def build_container_command(manifest: dict[str, Any], workspace: Path) -> list[str]:
    container = manifest["container"]
    working_directory = manifest["working_directory"].strip("/")
    container_workdir = "/workspace" if working_directory in {"", "."} else f"/workspace/{working_directory}"
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        container.get("user", "65534:65534"),
        "--volume",
        f"{workspace.resolve()}:/workspace:rw",
        "--workdir",
        container_workdir,
    ]
    for key, value in sorted(manifest.get("environment", {}).items()):
        command.extend(["--env", f"{key}={value}"])
    command.append(container["image"])
    command.extend(manifest["command"])
    return command


def _runtime_snapshot(mode: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "execution_mode": mode,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    if mode == "container":
        snapshot["docker_binary"] = shutil.which("docker")
    return snapshot


def _base_attestation(
    manifest: dict[str, Any],
    manifest_hash: str,
    workspace: Path,
    started_at: str,
) -> dict[str, Any]:
    return {
        "attestation_version": 1,
        "manifest_id": manifest.get("manifest_id"),
        "manifest_version": manifest.get("version"),
        "manifest_sha256": manifest_hash,
        "workspace": str(workspace.resolve()),
        "started_at": started_at,
        "finished_at": None,
        "duration_ms": None,
        "status": "blocked",
        "issues": [],
        "expected_exit_code": manifest.get("expected_exit_code"),
        "observed_exit_code": None,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "observed_outputs": [],
        "runtime": _runtime_snapshot(manifest.get("execution_mode", "unknown")),
    }


def _finish(
    attestation: dict[str, Any],
    status: str,
    started_monotonic: float,
    *,
    signing_key: bytes | None,
    key_id: str | None,
) -> ReproductionResult:
    if status not in STATUSES:
        raise ValueError(f"Unknown reproduction status: {status}")
    attestation["status"] = status
    attestation["finished_at"] = _utc_now()
    attestation["duration_ms"] = round((time.monotonic() - started_monotonic) * 1000)
    attestation["attestation_sha256"] = sha256_bytes(canonical_json(attestation).encode("utf-8"))
    if signing_key is not None:
        unsigned = dict(attestation)
        unsigned.pop("authentication", None)
        signature = hmac.new(
            signing_key,
            canonical_json(unsigned).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        attestation["authentication"] = {
            "algorithm": "hmac-sha256",
            "key_id": key_id or "unspecified",
            "signature": signature,
        }
    return ReproductionResult(status=status, attestation=attestation)


def verify_attestation_hmac(attestation: dict[str, Any], signing_key: bytes) -> bool:
    authentication = attestation.get("authentication")
    if not isinstance(authentication, dict) or authentication.get("algorithm") != "hmac-sha256":
        return False
    supplied = authentication.get("signature")
    if not isinstance(supplied, str):
        return False
    unsigned = dict(attestation)
    unsigned.pop("authentication", None)
    expected = hmac.new(
        signing_key,
        canonical_json(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(supplied, expected)


def run_reproduction(
    manifest_path: Path,
    schema_path: Path,
    workspace: Path,
    *,
    allow_execution: bool = False,
    signing_key: bytes | None = None,
    key_id: str | None = None,
) -> ReproductionResult:
    started_monotonic = time.monotonic()
    started_at = _utc_now()
    workspace = workspace.resolve()

    manifest_bytes = manifest_path.read_bytes()
    manifest_hash = sha256_bytes(manifest_bytes)
    manifest = json.loads(manifest_bytes)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    attestation = _base_attestation(manifest, manifest_hash, workspace, started_at)

    schema_issues = validate_reproduction_manifest(manifest, schema)
    if schema_issues:
        attestation["issues"].extend(schema_issues)
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    if not workspace.is_dir():
        attestation["issues"].append({
            "code": "missing_workspace",
            "path": "$.workspace",
            "message": f"Workspace does not exist: {workspace}",
        })
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    try:
        working_directory = _resolve_inside(workspace, manifest["working_directory"])
    except ValueError as exc:
        attestation["issues"].append({"code": "path_escape", "path": "$.working_directory", "message": str(exc)})
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    if not working_directory.is_dir():
        attestation["issues"].append({
            "code": "missing_working_directory",
            "path": "$.working_directory",
            "message": f"Working directory does not exist: {working_directory}",
        })
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    for index, item in enumerate(manifest["inputs"]):
        try:
            input_path = _resolve_inside(workspace, item["path"])
        except ValueError as exc:
            attestation["issues"].append({"code": "path_escape", "path": f"$.inputs.{index}.path", "message": str(exc)})
            continue
        if not input_path.is_file():
            attestation["issues"].append({
                "code": "missing_input",
                "path": f"$.inputs.{index}.path",
                "message": f"Input file not found: {item['path']}",
            })
            continue
        observed_hash = sha256_file(input_path)
        if observed_hash.lower() != item["sha256"].lower():
            attestation["issues"].append({
                "code": "input_hash_mismatch",
                "path": f"$.inputs.{index}.sha256",
                "message": f"Input SHA-256 mismatch for {item['path']}",
            })

    if attestation["issues"]:
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    output_paths: list[Path] = []
    for index, item in enumerate(manifest["outputs"]):
        try:
            output_path = _resolve_inside(workspace, item["path"])
        except ValueError as exc:
            attestation["issues"].append({"code": "path_escape", "path": f"$.outputs.{index}.path", "message": str(exc)})
            continue
        if output_path.exists():
            attestation["issues"].append({
                "code": "preexisting_output",
                "path": f"$.outputs.{index}.path",
                "message": f"Declared output already exists: {item['path']}",
            })
        output_paths.append(output_path)

    if attestation["issues"]:
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    if not allow_execution:
        attestation["issues"].append({
            "code": "execution_not_authorized",
            "path": "$.execution_mode",
            "message": "Execution requires explicit operator authorization.",
        })
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    if manifest["execution_mode"] == "container":
        if shutil.which("docker") is None:
            attestation["issues"].append({
                "code": "container_runtime_missing",
                "path": "$.execution_mode",
                "message": "Docker runtime is not available.",
            })
            return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)
        command = build_container_command(manifest, workspace)
        cwd = workspace
        environment = None
    else:
        command = manifest["command"]
        cwd = working_directory
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR"}
        }
        environment.update(manifest.get("environment", {}))

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            check=False,
            timeout=manifest["timeout_seconds"],
        )
        attestation["observed_exit_code"] = completed.returncode
        attestation["stdout_sha256"] = sha256_bytes(completed.stdout)
        attestation["stderr_sha256"] = sha256_bytes(completed.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        attestation["stdout_sha256"] = sha256_bytes(stdout)
        attestation["stderr_sha256"] = sha256_bytes(stderr)
        attestation["issues"].append({
            "code": "execution_timeout",
            "path": "$.timeout_seconds",
            "message": f"Execution exceeded {manifest['timeout_seconds']} seconds.",
        })
        return _finish(attestation, "mismatch", started_monotonic, signing_key=signing_key, key_id=key_id)
    except OSError as exc:
        attestation["issues"].append({
            "code": "execution_unavailable",
            "path": "$.command",
            "message": str(exc),
        })
        return _finish(attestation, "blocked", started_monotonic, signing_key=signing_key, key_id=key_id)

    status = "success"
    if attestation["observed_exit_code"] != manifest["expected_exit_code"]:
        attestation["issues"].append({
            "code": "exit_code_mismatch",
            "path": "$.expected_exit_code",
            "message": (
                f"Expected exit code {manifest['expected_exit_code']} but observed "
                f"{attestation['observed_exit_code']}"
            ),
        })
        status = "mismatch"

    for index, (item, output_path) in enumerate(zip(manifest["outputs"], output_paths, strict=True)):
        observed: dict[str, Any] = {
            "path": item["path"],
            "exists": output_path.is_file(),
            "sha256": None,
            "size_bytes": None,
        }
        if output_path.is_file():
            observed["sha256"] = sha256_file(output_path)
            observed["size_bytes"] = output_path.stat().st_size
        attestation["observed_outputs"].append(observed)

        if not observed["exists"]:
            code = "missing_required_output" if item["required"] else "missing_optional_output"
            attestation["issues"].append({
                "code": code,
                "path": f"$.outputs.{index}.path",
                "message": f"Output was not produced: {item['path']}",
            })
            status = "mismatch" if item["required"] else ("partial" if status == "success" else status)
            continue

        expected_hash = item.get("sha256")
        if expected_hash is None:
            attestation["issues"].append({
                "code": "output_hash_not_declared",
                "path": f"$.outputs.{index}.sha256",
                "message": f"Output exists but has no expected SHA-256: {item['path']}",
            })
            if status == "success":
                status = "partial"
        elif observed["sha256"].lower() != expected_hash.lower():
            attestation["issues"].append({
                "code": "output_hash_mismatch",
                "path": f"$.outputs.{index}.sha256",
                "message": f"Output SHA-256 mismatch for {item['path']}",
            })
            status = "mismatch"

    return _finish(attestation, status, started_monotonic, signing_key=signing_key, key_id=key_id)
