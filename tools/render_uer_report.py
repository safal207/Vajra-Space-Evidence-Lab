#!/usr/bin/env python3
"""Render deterministic human-readable Evidence Reports from UER records.

The report preserves the machine-readable evidence boundary while making it
reviewable by humans: observed/measured evidence, model outputs, claims,
assumptions, competing hypotheses, discriminating observations, and readiness.

Usage:
    python tools/render_uer_report.py
    python tools/render_uer_report.py --check
    python tools/render_uer_report.py records/example.uer.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = ROOT / "records"
REPORTS_DIR = ROOT / "reports"

OBSERVED_TYPES = {
    "direct_observation",
    "derived_measurement",
    "upper_limit",
    "non_detection",
    "negative_result",
    "statistical_result",
    "literature_evidence",
}
MODEL_TYPES = {"model_output", "simulation"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def refs(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def escape_table(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_report(record: dict[str, Any]) -> str:
    event = record["event"]
    title = " / ".join([event["id"], *event.get("aliases", [])])

    lines = [
        f"# Evidence Report — {title}",
        "",
        (
            f"> Generated from `{record['record_id']}` (UER v{record['uer_version']}). "
            "This file is generated from the machine-readable record; edit the UER JSON, "
            "not this report."
        ),
        "",
        "## Observed / measured evidence",
        "",
    ]

    for item in record.get("evidence", []):
        if item["evidence_type"] not in OBSERVED_TYPES:
            continue
        lines.extend(
            [
                f"- **{item['evidence_id']}** (`{item['evidence_type']}`): {item['statement']}",
                f"  - provenance: {refs(item.get('source_ids', []))}",
            ]
        )

    lines.extend(["", "## Model outputs", ""])
    model_items = [
        item
        for item in record.get("evidence", [])
        if item["evidence_type"] in MODEL_TYPES
    ]
    if model_items:
        for item in model_items:
            lines.extend(
                [
                    f"- **{item['evidence_id']}** (`{item['evidence_type']}`): {item['statement']}",
                    f"  - provenance: {refs(item.get('source_ids', []))}",
                ]
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Claims and inference boundary", ""])
    for claim in record.get("claims", []):
        lines.extend(
            [
                f"### {claim['claim_id']}",
                "",
                claim["text"],
                "",
                f"- type: `{claim['claim_type']}`",
                f"- status: `{claim.get('status') or 'unspecified'}`",
                f"- confidence: {claim.get('confidence') or 'unspecified'}",
                f"- supporting evidence: {refs(claim.get('supported_by', []))}",
                f"- contradicting evidence: {refs(claim.get('contradicted_by', []))}",
                f"- assumptions: {refs(claim.get('assumption_ids', []))}",
                "",
            ]
        )

    lines.extend(["## Assumptions", ""])
    for assumption in record.get("assumptions", []):
        lines.append(
            f"- **{assumption['assumption_id']}**: {assumption['description']}"
        )

    lines.extend(["", "## Competing hypotheses", ""])
    for hypothesis in record.get("hypotheses", []):
        lines.extend(
            [
                (
                    f"- **{hypothesis['hypothesis_id']}** — `{hypothesis['status']}`: "
                    f"{hypothesis['description']}"
                ),
                f"  - supporting evidence: {refs(hypothesis.get('supporting_evidence', []))}",
                f"  - contradicting evidence: {refs(hypothesis.get('contradicting_evidence', []))}",
            ]
        )

    lines.extend(["", "## What would discriminate", ""])
    for observation in record.get("discriminating_observations", []):
        lines.extend(
            [
                (
                    f"### {observation['observation_id']} — "
                    f"{observation.get('priority', 'unspecified')} priority"
                ),
                "",
                observation["description"],
                "",
                f"- tests: {refs(observation.get('discriminates_between', []))}",
            ]
        )
        outcomes = observation.get("expected_outcomes", {})
        if outcomes:
            lines.append("- expected outcomes:")
            for key, value in outcomes.items():
                lines.append(f"  - **{key}**: {value}")
        lines.append("")

    lines.extend(
        [
            "## Decision readiness",
            "",
            "| Context | Status | Rationale |",
            "|---|---|---|",
        ]
    )
    for item in record.get("readiness", []):
        lines.append(
            f"| {escape_table(item['context'])} | `{item['status']}` | "
            f"{escape_table(item['rationale'])} |"
        )

    lines.extend(["", "## Sources", ""])
    for source in record.get("sources", []):
        source_label = source.get("identifier") or source["title"]
        if source.get("url"):
            lead = f"[{source_label}]({source['url']})"
        else:
            lead = source_label
        status = (
            source.get("publication_status")
            or source.get("source_type")
            or "source"
        )
        lines.append(f"- {lead} — {status}")

    lines.extend(["", "## Integrity notes", ""])
    notes = record.get("notes", [])
    if notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("- none")
    lines.append("")

    return "\n".join(lines)


def report_path(record_path: Path, output_dir: Path) -> Path:
    stem = record_path.name.removesuffix(".uer.json")
    return output_dir / f"{stem}.evidence.md"


def resolve_record_paths(values: list[str]) -> list[Path]:
    if values:
        return [Path(value).resolve() for value in values]
    return sorted(RECORDS_DIR.glob("*.uer.json"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args(argv)

    record_paths = resolve_record_paths(args.records)
    if not record_paths:
        print("ERROR: no *.uer.json records found", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    stale: list[str] = []

    for record_path in record_paths:
        try:
            expected = render_report(load_json(record_path))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(f"ERROR: cannot render {record_path}: {exc}", file=sys.stderr)
            return 1

        destination = report_path(record_path, output_dir)
        if args.check:
            try:
                actual = destination.read_text(encoding="utf-8")
            except OSError:
                stale.append(f"missing generated report: {destination}")
                continue
            if actual != expected:
                stale.append(f"stale generated report: {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(expected, encoding="utf-8")
            print(f"Rendered {record_path} -> {destination}")

    if stale:
        print("UER report check failed:", file=sys.stderr)
        for error in stale:
            print(f"- {error}", file=sys.stderr)
        print(
            "Run `python tools/render_uer_report.py` and commit the generated report(s).",
            file=sys.stderr,
        )
        return 1

    if args.check:
        print(f"UER report check passed for {len(record_paths)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
