from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceAssessment:
    level: str
    reasons: tuple[str, ...]


def calculate_evidence_level(bundle: dict[str, Any]) -> EvidenceAssessment:
    reasons: list[str] = []

    provenance = bool(bundle.get("provenance_complete"))
    observation = bool(bundle.get("observation_present"))
    data_available = bool(bundle.get("data_available"))
    method_available = bool(bundle.get("method_available"))
    code_available = bool(bundle.get("code_available"))
    environment_pinned = bool(bundle.get("environment_pinned"))
    uncertainty_declared = bool(bundle.get("uncertainty_declared"))
    reproduced = bool(bundle.get("reproduced"))
    independent = bool(bundle.get("independent_confirmation"))
    multiple_channels = bool(bundle.get("multiple_independent_channels"))
    predictions = bool(bundle.get("successful_falsifiable_predictions"))

    if not provenance or not observation:
        return EvidenceAssessment(
            "S0",
            ("S0: missing complete provenance or inspectable observation.",),
        )

    level = "S1"
    reasons.append("S1: traceable provenance and at least one observation exist.")

    if not (data_available and method_available):
        return EvidenceAssessment(level, tuple(reasons))

    level = "S2"
    reasons.append("S2: data and method are inspectable.")

    if not (code_available and environment_pinned and uncertainty_declared and reproduced):
        return EvidenceAssessment(level, tuple(reasons))

    level = "S3"
    reasons.append(
        "S3: result reproduced from pinned code, environment, and declared uncertainty."
    )

    if not independent:
        return EvidenceAssessment(level, tuple(reasons))

    level = "S4"
    reasons.append("S4: materially independent confirmation exists.")

    if multiple_channels and predictions:
        level = "S5"
        reasons.append(
            "S5: multiple independent channels and successful falsifiable predictions exist."
        )

    return EvidenceAssessment(level, tuple(reasons))
