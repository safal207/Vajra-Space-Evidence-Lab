#!/usr/bin/env python3
"""Compute deterministic Evidence Readiness Scores for UER claims.

This score is NOT a probability that a scientific claim is true.
It measures how review-ready a claim is based on provenance, evidence directness,
inferential distance, assumption transparency, challenge coverage, and whether
there is a concrete discriminating path.

Usage:
    python tools/score_uer.py
    python tools/score_uer.py --check
    python tools/score_uer.py records/example.uer.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = ROOT / "records"
SCORES_DIR = ROOT / "scores"

EVIDENCE_DIRECTNESS = {
    "direct_observation": 20,
    "derived_measurement": 16,
    "statistical_result": 16,
    "upper_limit": 14,
    "non_detection": 14,
    "negative_result": 14,
    "literature_evidence": 12,
    "model_output": 6,
    "simulation": 6,
}

CLAIM_DISTANCE = {
    "observational": 20,
    "derived": 18,
    "statistical": 16,
    "interpretation": 10,
    "model_dependent": 5,
    "speculative": 2,
}

NEGATIVE_EVIDENCE = {"upper_limit", "non_detection", "negative_result"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def band(total: int) -> str:
    if total >= 85:
        return "REVIEW_READY"
    if total >= 70:
        return "CONDITIONAL"
    if total >= 50:
        return "LIMITED"
    return "INSUFFICIENT"


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    evidence_by_id = {item["evidence_id"]: item for item in record.get("evidence", [])}
    assumption_by_id = {
        item["assumption_id"]: item for item in record.get("assumptions", [])
    }
    hypotheses = record.get("hypotheses", [])
    discriminating = record.get("discriminating_observations", [])

    has_alternatives = len(hypotheses) >= 2 and any(
        item.get("status") in {"active", "unresolved", "disfavored"}
        for item in hypotheses
    )
    has_discriminating_path = any(
        len(item.get("discriminates_between", [])) >= 2 for item in discriminating
    )

    claim_scores: list[dict[str, Any]] = []

    for claim in record.get("claims", []):
        evidence_refs = [*claim.get("supported_by", []), *claim.get("contradicted_by", [])]
        linked_evidence = [evidence_by_id[ref] for ref in evidence_refs if ref in evidence_by_id]

        if linked_evidence and all(item.get("source_ids") for item in linked_evidence):
            provenance = 20
        elif linked_evidence:
            with_sources = sum(1 for item in linked_evidence if item.get("source_ids"))
            provenance = round(20 * with_sources / len(linked_evidence))
        else:
            provenance = 0

        supporting = [
            evidence_by_id[ref]
            for ref in claim.get("supported_by", [])
            if ref in evidence_by_id
        ]
        if supporting:
            directness = round(
                sum(EVIDENCE_DIRECTNESS.get(item["evidence_type"], 0) for item in supporting)
                / len(supporting)
            )
        else:
            directness = 0

        inferential_distance = CLAIM_DISTANCE.get(claim.get("claim_type"), 0)

        assumption_refs = claim.get("assumption_ids", [])
        claim_type = claim.get("claim_type")
        if claim_type in {"interpretation", "model_dependent", "speculative"}:
            if assumption_refs and all(
                assumption_by_id.get(ref, {}).get("source_ids") for ref in assumption_refs
            ):
                assumption_transparency = 15
            elif assumption_refs:
                assumption_transparency = 8
            else:
                assumption_transparency = 0
        else:
            assumption_transparency = 15

        has_negative_or_contradicting = bool(claim.get("contradicted_by")) or any(
            item.get("evidence_type") in NEGATIVE_EVIDENCE for item in supporting
        )
        if has_negative_or_contradicting:
            challenge_coverage = 15
        elif has_alternatives:
            challenge_coverage = 12
        else:
            challenge_coverage = 5

        discriminating_path = 10 if has_discriminating_path else 0

        components = {
            "provenance": provenance,
            "evidence_directness": directness,
            "inferential_distance": inferential_distance,
            "assumption_transparency": assumption_transparency,
            "challenge_coverage": challenge_coverage,
            "discriminating_path": discriminating_path,
        }
        total = sum(components.values())

        claim_scores.append(
            {
                "claim_id": claim["claim_id"],
                "claim_type": claim["claim_type"],
                "score": total,
                "band": band(total),
                "components": components,
                "interpretation": (
                    "Evidence readiness only; this score must not be interpreted as "
                    "the probability that the claim is true."
                ),
            }
        )

    totals = [item["score"] for item in claim_scores]
    summary = {
        "claims_scored": len(claim_scores),
        "minimum": min(totals) if totals else None,
        "maximum": max(totals) if totals else None,
    }

    return {
        "score_version": "0.1",
        "record_id": record["record_id"],
        "meaning": "Evidence readiness, not truth probability.",
        "max_score": 100,
        "bands": {
            "REVIEW_READY": "85-100",
            "CONDITIONAL": "70-84",
            "LIMITED": "50-69",
            "INSUFFICIENT": "0-49",
        },
        "dimensions": {
            "provenance": 20,
            "evidence_directness": 20,
            "inferential_distance": 20,
            "assumption_transparency": 15,
            "challenge_coverage": 15,
            "discriminating_path": 10,
        },
        "summary": summary,
        "claims": claim_scores,
    }


def score_path(record_path: Path, output_dir: Path) -> Path:
    stem = record_path.name.removesuffix(".uer.json")
    return output_dir / f"{stem}.readiness.json"


def resolve_record_paths(values: list[str]) -> list[Path]:
    if values:
        return [Path(value).resolve() for value in values]
    return sorted(RECORDS_DIR.glob("*.uer.json"))


def render_score(record: dict[str, Any]) -> str:
    return json.dumps(score_record(record), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=SCORES_DIR)
    args = parser.parse_args(argv)

    record_paths = resolve_record_paths(args.records)
    if not record_paths:
        print("ERROR: no *.uer.json records found", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    stale: list[str] = []

    for record_path in record_paths:
        try:
            expected = render_score(load_json(record_path))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(f"ERROR: cannot score {record_path}: {exc}", file=sys.stderr)
            return 1

        destination = score_path(record_path, output_dir)
        if args.check:
            try:
                actual = destination.read_text(encoding="utf-8")
            except OSError:
                stale.append(f"missing generated readiness score: {destination}")
                continue
            if actual != expected:
                stale.append(f"stale generated readiness score: {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(expected, encoding="utf-8")
            print(f"Scored {record_path} -> {destination}")

    if stale:
        print("UER readiness-score check failed:", file=sys.stderr)
        for error in stale:
            print(f"- {error}", file=sys.stderr)
        print(
            "Run `python tools/score_uer.py` and commit the generated score file(s).",
            file=sys.stderr,
        )
        return 1

    if args.check:
        print(f"UER readiness-score check passed for {len(record_paths)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
