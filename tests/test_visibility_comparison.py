from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/visibility-comparison.schema.json"
SCRIPT = ROOT / "scripts/analyze_m87_visibility_fit.py"


def valid_report() -> dict:
    return {
        "report_version": 1,
        "status": "complete",
        "method": {
            "method_id": "ehtim-1.1.0-image-chisq-v0.1",
            "library": "ehtim",
            "declared_version": "1.1.0",
            "transform_type": "nfft",
            "observables": ["amp", "cphase", "logcamp"],
        },
        "image": {
            "path": "image.fits",
            "sha256": "a" * 64,
            "size_bytes": 37440,
        },
        "bands": [
            {
                "band_id": "low",
                "uvfits": {
                    "path": "low.uvfits",
                    "sha256": "b" * 64,
                    "size_bytes": 650880,
                },
                "row_count": 100,
                "observables": [
                    {
                        "observable": "cphase",
                        "status": "success",
                        "reduced_chi_squared": 1.2,
                        "api_path": "image.chisq(obs,dtype=cphase,ttype=nfft)",
                        "issues": [],
                    }
                ],
            }
        ],
        "summary": {
            "requested_count": 1,
            "successful_count": 1,
            "failed_count": 0,
        },
        "limitations": ["Fixture report."],
    }


def test_visibility_comparison_schema_is_valid() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator.check_schema(schema) or [])
    assert errors == []


def test_valid_visibility_report_matches_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(valid_report())
    )
    assert errors == []


def test_partial_report_can_expose_unsupported_observables() -> None:
    report = valid_report()
    report["status"] = "partial"
    report["bands"][0]["observables"].append({
        "observable": "logcamp",
        "status": "unsupported",
        "reduced_chi_squared": None,
        "api_path": None,
        "issues": ["ValueError: unsupported data term"],
    })
    report["summary"] = {
        "requested_count": 2,
        "successful_count": 1,
        "failed_count": 1,
    }

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(report))
    assert errors == []


def test_visibility_analyzer_is_python_syntax_valid() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    compile(source, str(SCRIPT), "exec")
    assert "DEFAULT_OBSERVABLES = (\"vis\", \"amp\", \"cphase\", \"logcamp\")" in source
    assert "Reduced chi-squared values are not interpreted as an absolute acceptance verdict" in source
