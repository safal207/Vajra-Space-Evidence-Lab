from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import score_uer  # noqa: E402

RECORD_PATH = ROOT / "records" / "ep260321a-sn2026gzf.uer.json"


def load_record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def claim_result(scored: dict, claim_id: str) -> dict:
    return next(item for item in scored["claims"] if item["claim_id"] == claim_id)


def claim(record: dict, claim_id: str) -> dict:
    return next(item for item in record["claims"] if item["claim_id"] == claim_id)


def evidence(record: dict, evidence_id: str) -> dict:
    return next(item for item in record["evidence"] if item["evidence_id"] == evidence_id)


class EvidenceReadinessInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = load_record()
        self.baseline = score_uer.score_record(self.record)

    def test_pilot_scores_are_stable(self) -> None:
        expected = {
            "claim:association": (93, "REVIEW_READY"),
            "claim:shock-breakout": (78, "CONDITIONAL"),
            "claim:powerful-onaxis-jet": (76, "CONDITIONAL"),
            "claim:choked-outflow": (77, "CONDITIONAL"),
        }
        actual = {
            item["claim_id"]: (item["score"], item["band"])
            for item in self.baseline["claims"]
        }
        self.assertEqual(actual, expected)

    def test_losing_provenance_reduces_score(self) -> None:
        degraded = copy.deepcopy(self.record)
        evidence(degraded, "ev:ep-detection")["source_ids"] = []
        evidence(degraded, "ev:sn-classification")["source_ids"] = []

        baseline = claim_result(self.baseline, "claim:association")
        changed = claim_result(score_uer.score_record(degraded), "claim:association")

        self.assertEqual(baseline["components"]["provenance"], 20)
        self.assertEqual(changed["components"]["provenance"], 0)
        self.assertLess(changed["score"], baseline["score"])

    def test_greater_inferential_distance_reduces_score(self) -> None:
        degraded = copy.deepcopy(self.record)
        claim(degraded, "claim:shock-breakout")["claim_type"] = "model_dependent"

        baseline = claim_result(self.baseline, "claim:shock-breakout")
        changed = claim_result(score_uer.score_record(degraded), "claim:shock-breakout")

        self.assertEqual(baseline["components"]["inferential_distance"], 10)
        self.assertEqual(changed["components"]["inferential_distance"], 5)
        self.assertEqual(changed["score"], baseline["score"] - 5)

    def test_hiding_model_assumptions_reduces_score(self) -> None:
        degraded = copy.deepcopy(self.record)
        claim(degraded, "claim:choked-outflow")["assumption_ids"] = []

        baseline = claim_result(self.baseline, "claim:choked-outflow")
        changed = claim_result(score_uer.score_record(degraded), "claim:choked-outflow")

        self.assertEqual(baseline["components"]["assumption_transparency"], 15)
        self.assertEqual(changed["components"]["assumption_transparency"], 0)
        self.assertEqual(changed["score"], baseline["score"] - 15)

    def test_removing_discriminating_path_only_reduces_inferential_claims(self) -> None:
        degraded = copy.deepcopy(self.record)
        degraded["discriminating_observations"] = []
        changed_scores = score_uer.score_record(degraded)

        association_baseline = claim_result(self.baseline, "claim:association")
        association_changed = claim_result(changed_scores, "claim:association")
        self.assertEqual(association_baseline["components"]["discriminating_path"], 10)
        self.assertEqual(association_changed["components"]["discriminating_path"], 10)
        self.assertEqual(association_changed["score"], association_baseline["score"])

        for claim_id in (
            "claim:shock-breakout",
            "claim:powerful-onaxis-jet",
            "claim:choked-outflow",
        ):
            baseline = claim_result(self.baseline, claim_id)
            changed = claim_result(changed_scores, claim_id)
            self.assertEqual(baseline["components"]["discriminating_path"], 10)
            self.assertEqual(changed["components"]["discriminating_path"], 0)
            self.assertEqual(changed["score"], baseline["score"] - 10)

    def test_unrelated_event_hypotheses_do_not_inflate_derived_claim(self) -> None:
        degraded = copy.deepcopy(self.record)
        degraded["hypotheses"] = []
        degraded["discriminating_observations"] = []

        baseline = claim_result(self.baseline, "claim:association")
        changed = claim_result(score_uer.score_record(degraded), "claim:association")

        self.assertEqual(changed["components"]["challenge_coverage"], 12)
        self.assertEqual(changed["components"]["discriminating_path"], 10)
        self.assertEqual(changed["score"], baseline["score"])

    def test_removing_relevant_alternatives_penalizes_interpretive_claim(self) -> None:
        degraded = copy.deepcopy(self.record)
        degraded["hypotheses"] = []
        degraded["discriminating_observations"] = []

        baseline = claim_result(self.baseline, "claim:shock-breakout")
        changed = claim_result(score_uer.score_record(degraded), "claim:shock-breakout")

        self.assertEqual(baseline["components"]["challenge_coverage"], 12)
        self.assertEqual(changed["components"]["challenge_coverage"], 5)
        self.assertEqual(changed["components"]["discriminating_path"], 0)
        self.assertEqual(changed["score"], baseline["score"] - 17)

    def test_irrelevant_hypotheses_do_not_create_discriminating_credit(self) -> None:
        degraded = copy.deepcopy(self.record)
        for hypothesis in degraded["hypotheses"]:
            hypothesis["supporting_evidence"] = ["ev:ep-detection"]
            hypothesis["contradicting_evidence"] = []

        baseline = claim_result(self.baseline, "claim:shock-breakout")
        changed = claim_result(score_uer.score_record(degraded), "claim:shock-breakout")

        self.assertEqual(changed["components"]["challenge_coverage"], 5)
        self.assertEqual(changed["components"]["discriminating_path"], 0)
        self.assertEqual(changed["score"], baseline["score"] - 17)

    def test_band_boundaries_are_explicit(self) -> None:
        cases = {
            100: "REVIEW_READY",
            85: "REVIEW_READY",
            84: "CONDITIONAL",
            70: "CONDITIONAL",
            69: "LIMITED",
            50: "LIMITED",
            49: "INSUFFICIENT",
            0: "INSUFFICIENT",
        }
        for total, expected in cases.items():
            with self.subTest(total=total):
                self.assertEqual(score_uer.band(total), expected)


if __name__ == "__main__":
    unittest.main()
