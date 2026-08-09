#!/usr/bin/env python3
"""Negative/integrity tests for UER validation and generated surfaces."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.render_uer_graph import graph_path, main as graph_main
from tools.render_uer_report import main as report_main, report_path
from tools.score_uer import main as score_main, score_path
from tools.validate_uer import load_json, validate_semantics


CANONICAL_RECORD = ROOT / "records" / "ep260321a-sn2026gzf.uer.json"


class TestUERNegativeIntegrity(unittest.TestCase):
    def setUp(self) -> None:
        self.record = load_json(CANONICAL_RECORD)

    def semantic_errors(self, record: dict) -> list[str]:
        return validate_semantics(record, CANONICAL_RECORD)

    def test_missing_evidence_reference_is_rejected(self) -> None:
        broken = copy.deepcopy(self.record)
        claim = next(item for item in broken["claims"] if item["claim_id"] == "claim:association")
        claim["supported_by"].append("ev:missing")

        errors = self.semantic_errors(broken)
        self.assertTrue(
            any("references missing id 'ev:missing'" in error for error in errors),
            errors,
        )

    def test_model_dependent_claim_without_assumptions_is_rejected(self) -> None:
        broken = copy.deepcopy(self.record)
        claim = next(item for item in broken["claims"] if item["claim_id"] == "claim:choked-outflow")
        claim["assumption_ids"] = []

        errors = self.semantic_errors(broken)
        self.assertTrue(
            any("is model_dependent but has no assumption_ids" in error for error in errors),
            errors,
        )

    def test_evidence_free_speculative_claim_is_allowed(self) -> None:
        speculative = copy.deepcopy(self.record)
        claim = next(item for item in speculative["claims"] if item["claim_id"] == "claim:association")
        claim["claim_type"] = "speculative"
        claim["supported_by"] = []
        claim["contradicted_by"] = []

        errors = self.semantic_errors(speculative)
        self.assertFalse(
            any("has neither supporting nor contradicting evidence" in error for error in errors),
            errors,
        )

    def test_evidence_without_provenance_is_rejected(self) -> None:
        broken = copy.deepcopy(self.record)
        evidence = next(item for item in broken["evidence"] if item["evidence_id"] == "ev:ep-detection")
        evidence["source_ids"] = []

        errors = self.semantic_errors(broken)
        self.assertTrue(
            any("ev:ep-detection has no provenance source_ids" in error for error in errors),
            errors,
        )

    def test_duplicate_evidence_id_is_rejected(self) -> None:
        broken = copy.deepcopy(self.record)
        broken["evidence"].append(copy.deepcopy(broken["evidence"][0]))

        errors = self.semantic_errors(broken)
        self.assertTrue(
            any("duplicate evidence_id 'ev:ep-detection'" in error for error in errors),
            errors,
        )

    def test_missing_hypothesis_reference_is_rejected(self) -> None:
        broken = copy.deepcopy(self.record)
        broken["discriminating_observations"][0]["discriminates_between"].append("hyp:missing")

        errors = self.semantic_errors(broken)
        self.assertTrue(
            any("references missing id 'hyp:missing'" in error for error in errors),
            errors,
        )

    def test_stale_graph_fails_check_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            destination = graph_path(CANONICAL_RECORD, output_dir)
            destination.write_text("flowchart LR\n  stale[stale]\n", encoding="utf-8")
            result = graph_main([
                "--check",
                "--output-dir",
                str(output_dir),
                str(CANONICAL_RECORD),
            ])
            self.assertEqual(result, 1)

    def test_stale_report_fails_check_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            destination = report_path(CANONICAL_RECORD, output_dir)
            destination.write_text("# stale report\n", encoding="utf-8")
            result = report_main([
                "--check",
                "--output-dir",
                str(output_dir),
                str(CANONICAL_RECORD),
            ])
            self.assertEqual(result, 1)

    def test_stale_readiness_score_fails_check_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            destination = score_path(CANONICAL_RECORD, output_dir)
            destination.write_text(json.dumps({"stale": True}) + "\n", encoding="utf-8")
            result = score_main([
                "--check",
                "--output-dir",
                str(output_dir),
                str(CANONICAL_RECORD),
            ])
            self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
