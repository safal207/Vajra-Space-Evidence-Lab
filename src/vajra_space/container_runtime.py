from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .reproduction import canonical_json, sha256_bytes, sha256_file, validate_reproduction_manifest


SUPPORTED_RUNTIMES = ("docker", "podman")
STATUSES = ("success", "partial", "mismatch", "blocked")


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


def runtime_name(manifest: dict[str, Any]) -> str:
    return manifest.get("container", {}).get("runtime", "docker")


def build_oci_command(manifest: dict[str, Any], workspace: Path) -> list[str]:
    container = manifest["container"]
    runtime = runtime_name(manifest)
    if runtime not in SUPPORTED_RUNTIMES:
        raise ValueError(f"Unsupported container runtime: {runtime}")

    working_directory = manifest["working_directory"].strip("/")
    container_workdir = "/workspace" if working_directory in {"", "."} else f"/workspace/{working_directory}"
    command = [
        runtime,
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


def _finish(attestation: dict[str, Any], status: str, started: float) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"Unknown reproduction status: {status}")
    attestation["status"] = status
    attestation["finished_at"] = _utc_now()
    attestation["duration_ms"] = round((time.monotonic() - started) * 1000)
    unsigned = dict(attestation)
    unsigned.pop("attestation_sha256", None)
    attestation["attestation_sha256"] = sha256_bytes(canonical_json(unsigned).encode("utf-8"))
    return attestation


def execute_container_manifest(
    manifest_path: Path,
    schema_path: Path,
    workspace: Path,
    *,
    allow_execution: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    workspace = workspace.resolve()
    runtime = runtime_name(manifest)

    attestation: dict[str, Any] = {
        "attestation_version": 1,
        "manifest_id": manifest.get("manifest_id"),
        "manifest_version": manifest.get("version"),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "workspace": str(workspace),
        "started_at": _utc_now(),
        "finished_at": None,
        "duration_ms": None,
        "status": "blocked",
        "issues": [],
        "expected_exit_code": manifest.get("expected_exit_code"),
        "observed_exit_code": None,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "observed_outputs": [],
        "runtime": {
            "execution_mode": manifest.get("execution_mode"),
            "container_runtime": runtime,
            "binary": shutil.which(runtime),
            "image": manifest.get("container", {}).get("image"),
        },
    }

    issues = validate_reproduction_manifest(manifest, schema)
    attestation["issues"].extend(issues)
    if manifest.get("execution_mode") != "container":
        attestation["issues"].append({
            "code": "container_mode_required",
            "path": "$.execution_mode",
            "message": "This executor accepts container manifests only.",
        })
    if runtime not in SUPPORTED_RUNTIMES:
        attestation["issues"].append({
            "code": "unsupported_container_runtime",
            "path": "$.container.runtime",
            "message": f"Unsupported container runtime: {runtime}",
        })
    elif shutil.which(runtime) is None:
        attestation["issues"].append({
            "code": "container_runtime_missing",
            "path": "$.container.runtime",
            "message": f"Container runtime is not available: {runtime}",
        })
    if not workspace.is_dir():
        attestation["issues"].append({
            "code": "missing_workspace",
            "path": "$.workspace",
            "message": f"Workspace does not exist: {workspace}",
        })
    if attestation["issues"]:
        return _finish(attestation, "blocked", started)

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
        if sha256_file(input_path).lower() != item["sha256"].lower():
            attestation["issues"].append({
                "code": "input_hash_mismatch",
                "path": f"$.inputs.{index}.sha256",
                "message": f"Input SHA-256 mismatch for {item['path']}",
            })
    if attestation["issues"]:
        return _finish(attestation, "blocked", started)

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
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.append(output_path)
    if attestation["issues"]:
        return _finish(attestation, "blocked", started)
    if not allow_execution:
        attestation["issues"].append({
            "code": "execution_not_authorized",
            "path": "$.execution_mode",
            "message": "Execution requires explicit operator authorization.",
        })
        return _finish(attestation, "blocked", started)

    command = build_oci_command(manifest, workspace)
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            check=False,
            timeout=manifest["timeout_seconds"],
        )
        attestation["observed_exit_code"] = completed.returncode
        attestation["stdout_sha256"] = sha256_bytes(completed.stdout)
        attestation["stderr_sha256"] = sha256_bytes(completed.stderr)
    except subprocess.TimeoutExpired as exc:
        attestation["stdout_sha256"] = sha256_bytes(exc.stdout or b"")
        attestation["stderr_sha256"] = sha256_bytes(exc.stderr or b"")
        attestation["issues"].append({
            "code": "execution_timeout",
            "path": "$.timeout_seconds",
            "message": f"Execution exceeded {manifest['timeout_seconds']} seconds.",
        })
        return _finish(attestation, "mismatch", started)

    status = "success"
    if attestation["observed_exit_code"] != manifest["expected_exit_code"]:
        attestation["issues"].append({
            "code": "exit_code_mismatch",
            "path": "$.expected_exit_code",
            "message": f"Expected exit code {manifest['expected_exit_code']} but observed {attestation['observed_exit_code']}",
        })
        status = "mismatch"

    for index, (item, output_path) in enumerate(zip(manifest["outputs"], output_paths, strict=True)):
        observed = {
            "path": item["path"],
            "exists": output_path.is_file(),
            "sha256": sha256_file(output_path) if output_path.is_file() else None,
            "size_bytes": output_path.stat().st_size if output_path.is_file() else None,
        }
        attestation["observed_outputs"].append(observed)
        if not observed["exists"]:
            attestation["issues"].append({
                "code": "missing_required_output" if item["required"] else "missing_optional_output",
                "path": f"$.outputs.{index}.path",
                "message": f"Output was not produced: {item['path']}",
            })
            status = "mismatch" if item["required"] else ("partial" if status == "success" else status)
            continue
        expected = item.get("sha256")
        if expected is None:
            attestation["issues"].append({
                "code": "output_hash_not_declared",
                "path": f"$.outputs.{index}.sha256",
                "message": f"Output exists but has no expected SHA-256: {item['path']}",
            })
            if status == "success":
                status = "partial"
        elif observed["sha256"].lower() != expected.lower():
            attestation["issues"].append({
                "code": "output_hash_mismatch",
                "path": f"$.outputs.{index}.sha256",
                "message": f"Output SHA-256 mismatch for {item['path']}",
            })
            status = "mismatch"

    return _finish(attestation, status, started)
