from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .bundle import validate_bundle_file
from .scoring import calculate_evidence_level


ID_FIELDS = {
    "claim": "claim_id",
    "evidence": "evidence_id",
    "observation": "observation_id",
    "instrument": "instrument_id",
    "transformation": "transformation_id",
    "assumption": "assumption_id",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_json(path: Path, schema_path: Path) -> dict[str, Any]:
    value = read_json(path)
    schema = read_json(schema_path)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        messages = []
        for error in errors:
            location = "$" if not error.absolute_path else "$." + ".".join(
                str(part) for part in error.absolute_path
            )
            messages.append(f"{location}: {error.message}")
        raise ValueError(f"Invalid JSON document {path}: {'; '.join(messages)}")
    return value


def load_bundle_registry(bundle_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    bundle = read_json(bundle_path)
    registry: dict[str, dict[str, Any]] = {}
    for entry in bundle["objects"]:
        object_path = bundle_path.parent / entry["path"]
        obj = read_json(object_path)
        registry[entry["id"]] = {
            "kind": entry["kind"],
            "path": entry["path"],
            "sha256": entry["sha256"],
            "object": obj,
        }
    return bundle, registry


def _object_summary(registry_entry: dict[str, Any]) -> dict[str, Any]:
    obj = registry_entry["object"]
    kind = registry_entry["kind"]
    object_id = obj[ID_FIELDS[kind]]
    if kind == "observation":
        statement = obj["description"]
    elif kind == "transformation":
        statement = f"{obj['name']}: {obj['method']}"
    elif kind == "assumption":
        statement = obj["statement"]
    else:
        statement = obj.get("claim_text") or obj.get("name") or object_id
    return {
        "ref": object_id,
        "statement": statement,
        "source_path": registry_entry["path"],
        "source_sha256": registry_entry["sha256"],
    }


def _evidence_summary(registry_entry: dict[str, Any]) -> dict[str, Any]:
    obj = registry_entry["object"]
    return {
        "ref": obj["evidence_id"],
        "evidence_type": obj["evidence_type"],
        "source_uri": obj["source_uri"],
        "source_hash": obj["source_hash"],
        "uncertainty": obj["uncertainty"]["description"],
    }


def _alternative_summary(registry_entry: dict[str, Any]) -> dict[str, Any]:
    obj = registry_entry["object"]
    return {
        "claim_ref": obj["claim_id"],
        "text": obj["claim_text"],
        "status": obj["status"],
        "claim_type": obj["claim_type"],
    }


def build_m87_reconstruction_card(
    case_dir: Path,
    *,
    bundle_schema_path: Path,
    assessment_schema_path: Path,
) -> dict[str, Any]:
    bundle_path = case_dir / "evidence-bundle.json"
    assessment_path = case_dir / "claim-ring-image-assessment.json"

    bundle_result = validate_bundle_file(bundle_path, bundle_schema_path)
    if not bundle_result.valid:
        raise ValueError(
            "Invalid M87 evidence bundle: "
            + "; ".join(f"{item.path}: {item.message}" for item in bundle_result.issues)
        )

    assessment = _validate_json(assessment_path, assessment_schema_path)
    level = calculate_evidence_level(assessment)
    bundle, registry = load_bundle_registry(bundle_path)

    claim_ref = assessment["claim_ref"]
    claim_entry = registry[claim_ref]
    claim = claim_entry["object"]
    if level.level != claim["evidence_level"]:
        raise ValueError(
            f"Calculated evidence level {level.level} does not match claim level "
            f"{claim['evidence_level']}"
        )

    observation_entries = [
        entry for entry in registry.values() if entry["kind"] == "observation"
    ]
    transformation_entries = [
        registry[ref]
        for evidence_ref in claim["evidence_refs"]
        for ref in registry[evidence_ref]["object"].get("transformation_refs", [])
        if ref in registry
    ]
    assumption_entries = [registry[ref] for ref in claim["assumption_refs"]]
    evidence_entries = [registry[ref] for ref in claim["evidence_refs"]]
    alternative_entries = [registry[ref] for ref in claim["alternative_claim_refs"]]

    bootstrap = read_json(case_dir / "m87-ehtim-bootstrap-reproduction.json")
    podman = read_json(case_dir / "m87-ehtim-podman-confirmation.json")
    morphology = read_json(case_dir / "m87-eht-paper-morphology-run-30219587273.json")
    stability = read_json(case_dir / "m87-cross-run-stability-report.json")

    return {
        "card_id": "evidence-card:m87:ring-image:v1",
        "version": 1,
        "status": "scoped_complete",
        "title": "M87 Ring-Image Reconstruction Evidence Card",
        "scope": (
            "This card assesses only the REC claim that a ring-like image can be reconstructed "
            "from the declared calibrated VLBI inputs, code, parameters, and comparison contracts."
        ),
        "generated_from": {
            "bundle": {
                "path": "evidence-bundle.json",
                "sha256": sha256_file(bundle_path),
            },
            "assessment": {
                "path": "claim-ring-image-assessment.json",
                "sha256": sha256_file(assessment_path),
            },
        },
        "subject_claim": {
            "claim_ref": claim["claim_id"],
            "text": claim["claim_text"],
            "claim_type": claim["claim_type"],
            "status": claim["status"],
            "declared_evidence_level": claim["evidence_level"],
            "calculated_evidence_level": level.level,
            "version": claim["version"],
            "calculation_reasons": list(level.reasons),
        },
        "observations": sorted(
            (_object_summary(entry) for entry in observation_entries),
            key=lambda item: item["ref"],
        ),
        "transformations": sorted(
            {_object_summary(entry)["ref"]: _object_summary(entry) for entry in transformation_entries}.values(),
            key=lambda item: item["ref"],
        ),
        "assumptions": sorted(
            (_object_summary(entry) for entry in assumption_entries),
            key=lambda item: item["ref"],
        ),
        "evidence": sorted(
            (_evidence_summary(entry) for entry in evidence_entries),
            key=lambda item: item["ref"],
        ),
        "alternatives": sorted(
            (_alternative_summary(entry) for entry in alternative_entries),
            key=lambda item: item["claim_ref"],
        ),
        "reproduction": {
            "status": "success",
            "execution_families": [
                {
                    "family": "docker-podman-exact-family",
                    "fits_sha256": bootstrap["output"]["fits_sha256"],
                    "canonical_pixel_sha256": bootstrap["output"]["canonical_pixel_sha256"],
                    "docker_workflow_run_id": bootstrap["workflow"]["run_id"],
                    "podman_workflow_run_id": podman["workflow"]["run_id"],
                    "exact_runtime_match": podman["output"]["matches_prior_docker_fits"],
                },
                {
                    "family": "later-github-run",
                    "fits_sha256": morphology["output"]["fits_sha256"],
                    "canonical_pixel_sha256": morphology["output"]["canonical_pixel_sha256"],
                    "workflow_run_id": morphology["workflow"]["run_id"],
                    "exactly_matches_first_family": False,
                },
            ],
            "morphology": {
                "status": morphology["comparison"]["status"],
                "contract_id": morphology["comparison"]["contract_id"],
                "contract_status": morphology["comparison"]["contract_status"],
                "metrics": morphology["feature_extraction"]["metrics"],
            },
            "cross_run_stability": {
                "status": stability["status"],
                "contract_id": stability["contract_id"],
                "contract_status": stability["contract_status"],
                "measurements": stability["measurements"],
                "workflow_run_id": stability["workflow"]["run_id"],
                "artifact_digest": stability["workflow"]["artifact_digest"],
            },
            "public_signature": podman["signature"],
        },
        "open_requirements": sorted(set(bundle.get("missing", [])) | {
            "independent review of the Paper VI-derived feature extractor and thresholds",
            "independent operator or external-infrastructure reproduction",
            "investigation of cross-run numerical drift",
            "alternate CPU architecture or numerical-library execution",
            "visibility-domain and closure-quantity comparison",
        }),
        "limitations": [
            "The card is scoped to the REC reconstruction claim and does not assess the broader Kerr black-hole inference.",
            "Exact FITS and canonical-pixel hashes vary across workflow execution families despite fixed OCI, data, and code.",
            "Paper VI-derived feature extraction and cross-run tolerances are Vajra implementations and are not independently reviewed EHT code.",
            "Docker and Podman runtime diversity does not constitute independent scientific confirmation.",
            "The Ed25519 signature proves attestation integrity and key control, not scientific truth or trusted time.",
        ],
    }


def render_evidence_card_markdown(card: dict[str, Any]) -> str:
    claim = card["subject_claim"]
    lines = [
        f"# {card['title']}",
        "",
        f"> {claim['text']}",
        "",
        "## Verdict",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Claim type | `{claim['claim_type']}` |",
        f"| Status | `{claim['status']}` |",
        f"| Declared level | `{claim['declared_evidence_level']}` |",
        f"| Calculated level | `{claim['calculated_evidence_level']}` |",
        f"| Claim version | `{claim['version']}` |",
        "",
        card["scope"],
        "",
        "## Why this level",
        "",
    ]
    lines.extend(f"- {reason}" for reason in claim["calculation_reasons"])

    lines.extend(["", "## Evidence", ""])
    for item in card["evidence"]:
        lines.append(
            f"- **`{item['ref']}`** — `{item['evidence_type']}`; "
            f"source hash `{item['source_hash']}`. {item['uncertainty']}"
        )

    lines.extend(["", "## Reproduction", ""])
    morphology = card["reproduction"]["morphology"]
    metrics = morphology["metrics"]
    lines.extend([
        f"- Paper-derived morphology contract: `{morphology['status']}`",
        f"- Mean diameter: `{metrics['mean_diameter_microarcseconds']:.4f} μas`",
        f"- Mean radial FWHM: `{metrics['mean_fwhm_microarcseconds']:.4f} μas`",
        f"- Fractional width: `{metrics['fractional_width']:.5f}`",
        f"- Circularity fractional spread: `{metrics['circularity_fractional_spread']:.5f}`",
        f"- Cross-run stability: `{card['reproduction']['cross_run_stability']['status']}`",
    ])

    lines.extend(["", "## Competing alternatives", ""])
    for item in card["alternatives"]:
        lines.append(
            f"- **`{item['claim_ref']}`** — `{item['claim_type']}` / `{item['status']}`: {item['text']}"
        )

    lines.extend(["", "## Open requirements", ""])
    lines.extend(f"- {item}" for item in card["open_requirements"])

    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in card["limitations"])
    lines.append("")
    return "\n".join(lines)
