from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from vajra_space.evidence_card import (
    build_m87_reconstruction_card,
    render_evidence_card_markdown,
)
from vajra_space.scoring import calculate_evidence_level


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"
ASSESSMENT = CASE / "claim-ring-image-assessment.json"
BUNDLE = CASE / "evidence-bundle.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_card() -> dict:
    return build_m87_reconstruction_card(
        CASE,
        bundle_schema_path=ROOT / "schemas/bundle.schema.json",
        assessment_schema_path=ROOT / "schemas/evidence-assessment.schema.json",
    )


def test_m87_assessment_is_schema_valid_and_calculates_s3() -> None:
    assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas/evidence-assessment.schema.json").read_text(encoding="utf-8")
    )
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(assessment)
    )

    assert errors == []
    calculated = calculate_evidence_level(assessment)
    assert calculated.level == "S3"
    assert assessment["reproduced"] is True
    assert assessment["independent_confirmation"] is False
    assert assessment["multiple_independent_channels"] is False
    assert assessment["successful_falsifiable_predictions"] is False


def test_generated_card_is_schema_valid_and_level_is_calculated() -> None:
    card = build_card()
    schema = json.loads(
        (ROOT / "schemas/evidence-card.schema.json").read_text(encoding="utf-8")
    )
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(card)
    )

    assert errors == []
    claim = card["subject_claim"]
    assert claim["claim_type"] == "REC"
    assert claim["status"] == "supported"
    assert claim["declared_evidence_level"] == "S3"
    assert claim["calculated_evidence_level"] == "S3"
    assert claim["version"] == 4
    assert any(reason.startswith("S3:") for reason in claim["calculation_reasons"])
    assert not any(reason.startswith("S4:") for reason in claim["calculation_reasons"])


def test_card_binds_exact_bundle_and_assessment_bytes() -> None:
    card = build_card()

    assert card["generated_from"] == {
        "bundle": {
            "path": "evidence-bundle.json",
            "sha256": sha256_file(BUNDLE),
        },
        "assessment": {
            "path": "claim-ring-image-assessment.json",
            "sha256": sha256_file(ASSESSMENT),
        },
    }


def test_card_contains_linked_evidence_alternatives_and_reproduction() -> None:
    card = build_card()
    evidence_refs = {item["ref"] for item in card["evidence"]}
    alternative_refs = {item["claim_ref"] for item in card["alternatives"]}

    assert evidence_refs == {
        "evidence:m87:ehtim-bootstrap-reproduction",
        "evidence:m87:ehtim-podman-runtime-confirmation",
        "evidence:m87:paper-derived-morphology-stability",
    }
    assert alternative_refs == {
        "claim:m87:calibration-artifact",
        "claim:m87:imaging-prior-artifact",
        "claim:m87:jet-only-morphology",
        "claim:m87:non-kerr-compact-object",
        "claim:m87:variability-bias",
    }
    assert card["reproduction"]["status"] == "success"
    assert card["reproduction"]["morphology"]["status"] == "pass"
    assert card["reproduction"]["cross_run_stability"]["status"] == "pass"
    assert card["reproduction"]["public_signature"]["algorithm"] == "ed25519"


def test_card_is_scoped_and_cannot_be_read_as_kerr_s4_verdict() -> None:
    card = build_card()
    combined_limitations = " ".join(card["limitations"])
    open_requirements = " ".join(card["open_requirements"])

    assert card["status"] == "scoped_complete"
    assert "only the REC claim" in card["scope"]
    assert "does not assess the broader Kerr" in combined_limitations
    assert "independent scientific confirmation" in combined_limitations
    assert "independent operator" in open_requirements
    assert "visibility-domain" in open_requirements


def test_markdown_card_contains_verdict_evidence_and_open_requirements() -> None:
    markdown = render_evidence_card_markdown(build_card())

    assert markdown.startswith("# M87 Ring-Image Reconstruction Evidence Card")
    assert "| Calculated level | `S3` |" in markdown
    assert "## Evidence" in markdown
    assert "evidence:m87:paper-derived-morphology-stability" in markdown
    assert "Mean diameter: `41.0708 μas`" in markdown
    assert "## Competing alternatives" in markdown
    assert "## Open requirements" in markdown
    assert "## Limitations" in markdown
    assert "does not assess the broader Kerr" in markdown


def test_card_generation_is_deterministic() -> None:
    first = json.dumps(build_card(), sort_keys=True, ensure_ascii=False)
    second = json.dumps(build_card(), sort_keys=True, ensure_ascii=False)
    assert first == second
