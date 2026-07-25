from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ID_FIELDS = {
    "claim": "claim_id",
    "evidence": "evidence_id",
    "observation": "observation_id",
    "instrument": "instrument_id",
    "transformation": "transformation_id",
    "assumption": "assumption_id",
}

REFERENCE_FIELDS = {
    "claim": ("evidence_refs", "assumption_refs", "alternative_claim_refs"),
    "evidence": ("instrument_ref", "transformation_refs"),
    "observation": ("instrument_ref",),
    "instrument": ("calibration_evidence_refs",),
    "transformation": ("input_refs", "output_ref"),
    "assumption": ("evidence_refs",),
}


@dataclass(frozen=True)
class BundleIssue:
    code: str
    message: str
    path: str


@dataclass(frozen=True)
class BundleValidation:
    valid: bool
    issues: tuple[BundleIssue, ...]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_refs(kind: str, obj: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for field in REFERENCE_FIELDS[kind]:
        value = obj.get(field)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for ref in values:
            if isinstance(ref, str):
                refs.append((field, ref))
    return refs


def validate_bundle_file(bundle_path: Path, schema_path: Path) -> BundleValidation:
    issues: list[BundleIssue] = []
    bundle = _read_json(bundle_path)
    schema = _read_json(schema_path)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors = sorted(validator.iter_errors(bundle), key=lambda error: list(error.absolute_path))
    for error in schema_errors:
        path = "$" if not error.absolute_path else "$." + ".".join(str(part) for part in error.absolute_path)
        issues.append(BundleIssue("schema_error", error.message, path))
    if issues:
        return BundleValidation(False, tuple(issues))

    base = bundle_path.parent.resolve()
    registry: dict[str, tuple[str, dict[str, Any]]] = {}

    for index, entry in enumerate(bundle["objects"]):
        object_id = entry["id"]
        kind = entry["kind"]
        entry_path = f"$.objects.{index}"

        if object_id in registry:
            issues.append(BundleIssue("duplicate_id", f"Duplicate object id: {object_id}", entry_path + ".id"))
            continue

        candidate = (base / entry["path"]).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            issues.append(BundleIssue("path_escape", "Object path escapes the bundle directory.", entry_path + ".path"))
            continue

        if not candidate.is_file():
            issues.append(BundleIssue("missing_object", f"Object file not found: {entry['path']}", entry_path + ".path"))
            continue

        actual_hash = _sha256(candidate)
        if actual_hash.lower() != entry["sha256"].lower():
            issues.append(BundleIssue("hash_mismatch", f"SHA-256 mismatch for {object_id}", entry_path + ".sha256"))
            continue

        try:
            obj = _read_json(candidate)
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(BundleIssue("invalid_object_json", str(exc), entry_path + ".path"))
            continue

        id_field = ID_FIELDS[kind]
        if obj.get(id_field) != object_id:
            issues.append(BundleIssue("id_mismatch", f"Manifest id does not match {id_field} in object.", entry_path + ".id"))
            continue

        registry[object_id] = (kind, obj)

    for root_index, root_ref in enumerate(bundle["root_claim_refs"]):
        target = registry.get(root_ref)
        if target is None:
            issues.append(BundleIssue("dangling_root_claim", f"Missing root claim: {root_ref}", f"$.root_claim_refs.{root_index}"))
        elif target[0] != "claim":
            issues.append(BundleIssue("root_not_claim", f"Root reference is not a claim: {root_ref}", f"$.root_claim_refs.{root_index}"))

    for object_id, (kind, obj) in registry.items():
        for field, ref in _iter_refs(kind, obj):
            if ref not in registry:
                issues.append(BundleIssue("dangling_reference", f"{object_id}.{field} references missing object {ref}", f"$[{object_id}].{field}"))

    return BundleValidation(not issues, tuple(issues))
