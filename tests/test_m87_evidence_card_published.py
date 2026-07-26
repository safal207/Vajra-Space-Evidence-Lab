from __future__ import annotations

import json
from pathlib import Path

from vajra_space.evidence_card import (
    build_m87_reconstruction_card,
    render_evidence_card_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/m87-black-hole"
PUBLISHED_JSON = CASE / "M87-RECONSTRUCTION-EVIDENCE-CARD.json"
PUBLISHED_MARKDOWN = CASE / "M87-RECONSTRUCTION-EVIDENCE-CARD.md"


def generated_card() -> dict:
    return build_m87_reconstruction_card(
        CASE,
        bundle_schema_path=ROOT / "schemas/bundle.schema.json",
        assessment_schema_path=ROOT / "schemas/evidence-assessment.schema.json",
    )


def test_published_json_matches_fresh_generation_byte_for_byte() -> None:
    expected = json.dumps(
        generated_card(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"
    assert PUBLISHED_JSON.read_text(encoding="utf-8") == expected


def test_published_markdown_matches_fresh_generation_byte_for_byte() -> None:
    expected = render_evidence_card_markdown(generated_card())
    assert PUBLISHED_MARKDOWN.read_text(encoding="utf-8") == expected


def test_published_card_is_scoped_s3_not_s4() -> None:
    card = json.loads(PUBLISHED_JSON.read_text(encoding="utf-8"))

    assert card["status"] == "scoped_complete"
    assert card["subject_claim"]["claim_type"] == "REC"
    assert card["subject_claim"]["calculated_evidence_level"] == "S3"
    assert "independent operator or external-infrastructure reproduction" in card["open_requirements"]
    assert any(
        "does not constitute independent scientific confirmation" in limitation
        for limitation in card["limitations"]
    )
