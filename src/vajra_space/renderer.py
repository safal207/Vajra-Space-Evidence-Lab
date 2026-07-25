from __future__ import annotations

from typing import Any


def render_claim_markdown(claim: dict[str, Any]) -> str:
    evidence_refs = claim.get("evidence_refs", [])
    assumptions = claim.get("assumption_refs", [])
    alternatives = claim.get("alternative_claim_refs", [])

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- `{item}`" for item in items) if items else "- None declared"

    return f"""# Evidence Card: {claim['claim_id']}

> {claim['claim_text']}

| Field | Value |
|---|---|
| Type | `{claim['claim_type']}` |
| Status | `{claim['status']}` |
| Evidence level | `{claim['evidence_level']}` |
| Version | `{claim['version']}` |
| Created | `{claim['created_at']}` |

## Evidence references

{bullets(evidence_refs)}

## Assumptions

{bullets(assumptions)}

## Alternative claims

{bullets(alternatives)}

## Integrity note

This card separates observation, reconstruction, inference, simulation, prediction, and speculation.
A higher evidence level must be justified by inspectable evidence and reproducibility, not confidence language.
"""
