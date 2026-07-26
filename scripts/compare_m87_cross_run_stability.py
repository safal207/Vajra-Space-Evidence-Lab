from __future__ import division, print_function

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from astropy.io import fits


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_image(path):
    with fits.open(str(path), memmap=False) as hdul:
        hdu = next(item for item in hdul if item.data is not None)
        image = np.asarray(hdu.data, dtype=float).squeeze()
    if image.ndim != 2:
        raise ValueError("Expected a 2-D FITS image")
    image = image.copy()
    image[~np.isfinite(image)] = 0.0
    return image


def metric(document, dotted_path):
    current = document
    for part in dotted_path.split("."):
        current = current[part]
    return current


def evaluate(value, comparator):
    if comparator["operator"] == "max":
        return value <= comparator["threshold"]
    if comparator["operator"] == "min":
        return value >= comparator["threshold"]
    raise ValueError("Unsupported operator: {}".format(comparator["operator"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-fits", type=Path, required=True)
    parser.add_argument("--candidate-fits", type=Path, required=True)
    parser.add_argument("--reference-features", type=Path, required=True)
    parser.add_argument("--candidate-features", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))

    reference = read_image(args.reference_fits)
    candidate = read_image(args.candidate_fits)
    if reference.shape != candidate.shape:
        raise ValueError("FITS shapes differ: {} vs {}".format(reference.shape, candidate.shape))

    difference = candidate - reference
    reference_l1 = float(np.sum(np.abs(reference)))
    reference_l2 = float(np.linalg.norm(reference))
    correlation = float(np.corrcoef(reference.ravel(), candidate.ravel())[0, 1])

    reference_features = json.loads(args.reference_features.read_text(encoding="utf-8"))
    candidate_features = json.loads(args.candidate_features.read_text(encoding="utf-8"))
    reference_metrics = reference_features["metrics"]
    candidate_metrics = candidate_features["metrics"]

    values = {
        "image": {
            "pixel_correlation": correlation,
            "relative_l1_difference": (
                None if reference_l1 == 0 else float(np.sum(np.abs(difference))) / reference_l1
            ),
            "relative_l2_difference": (
                None if reference_l2 == 0 else float(np.linalg.norm(difference)) / reference_l2
            ),
            "maximum_absolute_pixel_difference": float(np.max(np.abs(difference))),
            "mean_absolute_pixel_difference": float(np.mean(np.abs(difference))),
            "rmse": float(np.sqrt(np.mean(difference ** 2))),
        },
        "morphology": {
            "mean_diameter_absolute_delta_microarcseconds": abs(
                float(candidate_metrics["mean_diameter_microarcseconds"])
                - float(reference_metrics["mean_diameter_microarcseconds"])
            ),
            "mean_fwhm_absolute_delta_microarcseconds": abs(
                float(candidate_metrics["mean_fwhm_microarcseconds"])
                - float(reference_metrics["mean_fwhm_microarcseconds"])
            ),
            "fractional_width_absolute_delta": abs(
                float(candidate_metrics["fractional_width"])
                - float(reference_metrics["fractional_width"])
            ),
            "circularity_absolute_delta": abs(
                float(candidate_metrics["circularity_fractional_spread"])
                - float(reference_metrics["circularity_fractional_spread"])
            ),
        },
    }

    comparator_results = []
    all_passed = True
    for comparator in sorted(contract["comparators"], key=lambda item: item["comparator_id"]):
        observed = float(metric(values, comparator["metric_path"]))
        passed = bool(evaluate(observed, comparator))
        all_passed = all_passed and passed
        comparator_results.append({
            "comparator_id": comparator["comparator_id"],
            "metric_path": comparator["metric_path"],
            "operator": comparator["operator"],
            "threshold": comparator["threshold"],
            "observed": observed,
            "passed": passed,
            "basis": comparator["basis"],
        })

    report = {
        "report_version": 1,
        "status": "pass" if all_passed else "mismatch",
        "contract_id": contract["contract_id"],
        "contract_version": contract["version"],
        "contract_status": contract["status"],
        "claim_ref": contract["claim_ref"],
        "reference": {
            "workflow_run_id": contract["reference"]["workflow_run_id"],
            "artifact_id": contract["reference"]["artifact_id"],
            "fits_sha256": sha256_file(args.reference_fits),
            "feature_report_sha256": sha256_file(args.reference_features),
            "metrics": reference_metrics,
        },
        "candidate": {
            "workflow_run_id": contract["candidate"]["workflow_run_id"],
            "artifact_id": contract["candidate"]["artifact_id"],
            "fits_sha256": sha256_file(args.candidate_fits),
            "feature_report_sha256": sha256_file(args.candidate_features),
            "metrics": candidate_metrics,
        },
        "measurements": values,
        "comparators": comparator_results,
        "limitations": contract["limitations"],
        "inputs": {
            "contract_sha256": sha256_file(args.contract),
            "schema_sha256": sha256_file(args.schema),
        },
    }

    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if all_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
