from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_value(left: Any, right: Any) -> dict[str, Any]:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        absolute_delta = abs(float(left) - float(right))
        scale = max(abs(float(left)), abs(float(right)), 1.0)
        return {
            "equal": left == right,
            "absolute_delta": absolute_delta,
            "relative_delta": absolute_delta / scale,
        }
    return {"equal": left == right}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run1-fits", type=Path, required=True)
    parser.add_argument("--run2-fits", type=Path, required=True)
    parser.add_argument("--run1-metrics", type=Path, required=True)
    parser.add_argument("--run2-metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--oci-reference", required=True)
    parser.add_argument("--data-commit", required=True)
    parser.add_argument("--imaging-commit", required=True)
    args = parser.parse_args()

    first = json.loads(args.run1_metrics.read_text(encoding="utf-8"))
    second = json.loads(args.run2_metrics.read_text(encoding="utf-8"))
    first_metrics = first["metrics"]
    second_metrics = second["metrics"]

    diagnostic_keys = [
        "canonical_pixel_sha256",
        "shape",
        "sum",
        "maximum",
        "centroid_x_pixels",
        "centroid_y_pixels",
        "diameter_microarcseconds",
        "fwhm_microarcseconds",
        "orientation_degrees_diagnostic",
        "rotational_asymmetry_l1",
    ]
    comparisons = {
        key: compare_value(first_metrics.get(key), second_metrics.get(key))
        for key in diagnostic_keys
    }

    run1_hash = sha256_file(args.run1_fits)
    run2_hash = sha256_file(args.run2_fits)
    exact_file_match = run1_hash == run2_hash
    exact_pixel_match = (
        first_metrics["canonical_pixel_sha256"]
        == second_metrics["canonical_pixel_sha256"]
    )

    report = {
        "report_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "exact_match" if exact_file_match else (
            "pixel_match_header_difference" if exact_pixel_match else "output_mismatch"
        ),
        "environment": {
            "oci_reference": args.oci_reference,
            "network_during_container_execution": "disabled",
        },
        "sources": {
            "data_commit": args.data_commit,
            "imaging_commit": args.imaging_commit,
        },
        "run1": {
            "fits_sha256": run1_hash,
            "metrics_sha256": sha256_file(args.run1_metrics),
            "canonical_pixel_sha256": first_metrics["canonical_pixel_sha256"],
        },
        "run2": {
            "fits_sha256": run2_hash,
            "metrics_sha256": sha256_file(args.run2_metrics),
            "canonical_pixel_sha256": second_metrics["canonical_pixel_sha256"],
        },
        "exact_fits_byte_match": exact_file_match,
        "exact_canonical_pixel_match": exact_pixel_match,
        "diagnostic_comparisons": comparisons,
        "interpretation_limit": "This report measures repeatability inside one pinned OCI environment. It does not yet establish agreement with an independently reviewed scientific reference image or EHT ring-measurement pipeline.",
    }

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
