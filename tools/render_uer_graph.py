#!/usr/bin/env python3
"""Render deterministic Mermaid graphs from Unified Evidence Record files.

The graph makes provenance and reasoning links reviewable in a pull request:
source -> evidence -> claim/hypothesis -> discriminating observation.

Usage:
    python tools/render_uer_graph.py
    python tools/render_uer_graph.py --check
    python tools/render_uer_graph.py records/example.uer.json
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = ROOT / "records"
GRAPHS_DIR = ROOT / "graphs"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def node_id(prefix: str, raw_id: str) -> str:
    digest = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def label(*parts: object) -> str:
    safe_parts: list[str] = []
    for part in parts:
        if part is None:
            continue
        safe = html.escape(str(part), quote=True).replace("&quot;", "'")
        safe_parts.append(safe)
    return "<br/>".join(safe_parts)


def render_graph(record: dict[str, Any]) -> str:
    event = record["event"]
    event_id = event["id"]
    event_node = node_id("event", event_id)

    lines = ["flowchart LR"]
    lines.append(
        f'  {event_node}["{label(event_id, *event.get("aliases", []))}"]'
    )

    sections = [
        ("Sources", record.get("sources", []), "source_id", "source_type", "src"),
        ("Evidence", record.get("evidence", []), "evidence_id", "evidence_type", "ev"),
        ("Claims", record.get("claims", []), "claim_id", "claim_type", "claim"),
        ("Assumptions", record.get("assumptions", []), "assumption_id", None, "assumption"),
        ("Hypotheses", record.get("hypotheses", []), "hypothesis_id", "status", "hyp"),
        (
            "Next observations",
            record.get("discriminating_observations", []),
            "observation_id",
            "priority",
            "obs",
        ),
    ]

    nodes: dict[str, str] = {}
    for title, items, id_field, type_field, prefix in sections:
        lines.append(f"  subgraph {prefix}_group[{title}]")
        for item in items:
            raw_id = item[id_field]
            mermaid_id = node_id(prefix, raw_id)
            nodes[raw_id] = mermaid_id
            detail = item.get(type_field) if type_field else None
            lines.append(f'    {mermaid_id}["{label(raw_id, detail)}"]')
        lines.append("  end")

    for item in record.get("evidence", []):
        evidence_node = nodes[item["evidence_id"]]
        lines.append(f"  {event_node} -->|contains| {evidence_node}")
        for source_id in item.get("source_ids", []):
            lines.append(f"  {nodes[source_id]} -->|provenance| {evidence_node}")

    for item in record.get("claims", []):
        claim_node = nodes[item["claim_id"]]
        for evidence_id in item.get("supported_by", []):
            lines.append(f"  {nodes[evidence_id]} -->|supports| {claim_node}")
        for evidence_id in item.get("contradicted_by", []):
            lines.append(f"  {nodes[evidence_id]} -->|contradicts| {claim_node}")
        for assumption_id in item.get("assumption_ids", []):
            lines.append(f"  {nodes[assumption_id]} -->|assumption| {claim_node}")

    for item in record.get("hypotheses", []):
        hypothesis_node = nodes[item["hypothesis_id"]]
        for evidence_id in item.get("supporting_evidence", []):
            lines.append(f"  {nodes[evidence_id]} -->|supports| {hypothesis_node}")
        for evidence_id in item.get("contradicting_evidence", []):
            lines.append(f"  {nodes[evidence_id]} -->|contradicts| {hypothesis_node}")

    for item in record.get("discriminating_observations", []):
        observation_node = nodes[item["observation_id"]]
        for hypothesis_id in item.get("discriminates_between", []):
            lines.append(f"  {nodes[hypothesis_id]} -->|tested by| {observation_node}")

    return "\n".join(lines) + "\n"


def graph_path(record_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{record_path.name.removesuffix('.json')}.mmd"


def resolve_record_paths(values: list[str]) -> list[Path]:
    if values:
        return [Path(value).resolve() for value in values]
    return sorted(RECORDS_DIR.glob("*.uer.json"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=GRAPHS_DIR)
    args = parser.parse_args(argv)

    record_paths = resolve_record_paths(args.records)
    if not record_paths:
        print("ERROR: no *.uer.json records found", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    stale: list[str] = []

    for record_path in record_paths:
        try:
            expected = render_graph(load_json(record_path))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(f"ERROR: cannot render {record_path}: {exc}", file=sys.stderr)
            return 1

        destination = graph_path(record_path, output_dir)
        if args.check:
            try:
                actual = destination.read_text(encoding="utf-8")
            except OSError:
                stale.append(f"missing generated graph: {destination}")
                continue
            if actual != expected:
                stale.append(f"stale generated graph: {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(expected, encoding="utf-8")
            print(f"Rendered {record_path} -> {destination}")

    if stale:
        print("UER graph check failed:", file=sys.stderr)
        for error in stale:
            print(f"- {error}", file=sys.stderr)
        print(
            "Run `python tools/render_uer_graph.py` and commit the generated graph(s).",
            file=sys.stderr,
        )
        return 1

    if args.check:
        print(f"UER graph check passed for {len(record_paths)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
