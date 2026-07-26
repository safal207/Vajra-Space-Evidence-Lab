from __future__ import division, print_function

import argparse
import hashlib
import json
import math
from pathlib import Path

import pkg_resources

import ehtim as eh


METHOD_ID = "ehtim-1.1.0-image-chisq-v0.1"
DEFAULT_OBSERVABLES = ("vis", "amp", "cphase", "logcamp")
TRANSFORM_CANDIDATES = ("nfft", "fast", "direct")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path):
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def load_uvfits(path):
    loaders = []
    if hasattr(eh, "obsdata") and hasattr(eh.obsdata, "load_uvfits"):
        loaders.append(("ehtim.obsdata.load_uvfits", eh.obsdata.load_uvfits))
    if hasattr(eh, "obsdata") and hasattr(eh.obsdata, "Obsdata"):
        candidate = getattr(eh.obsdata.Obsdata, "load_uvfits", None)
        if candidate is not None:
            loaders.append(("ehtim.obsdata.Obsdata.load_uvfits", candidate))

    errors = []
    for name, loader in loaders:
        try:
            return loader(str(path)), name
        except Exception as exc:
            errors.append("{}: {}: {}".format(name, type(exc).__name__, exc))
    raise RuntimeError("Unable to load UVFITS: " + "; ".join(errors))


def load_image(path):
    loaders = []
    if hasattr(eh, "image") and hasattr(eh.image, "load_fits"):
        loaders.append(("ehtim.image.load_fits", eh.image.load_fits))
    if hasattr(eh, "image") and hasattr(eh.image, "Image"):
        candidate = getattr(eh.image.Image, "load_fits", None)
        if candidate is not None:
            loaders.append(("ehtim.image.Image.load_fits", candidate))

    errors = []
    for name, loader in loaders:
        try:
            return loader(str(path)), name
        except Exception as exc:
            errors.append("{}: {}: {}".format(name, type(exc).__name__, exc))
    raise RuntimeError("Unable to load FITS image: " + "; ".join(errors))


def candidate_calls(image, obs, observable):
    calls = []
    image_method = getattr(image, "chisq", None)
    if image_method is not None:
        for transform in TRANSFORM_CANDIDATES:
            calls.append((
                "image.chisq(obs,dtype={},ttype={})".format(observable, transform),
                lambda method=image_method, value=observable, ttype=transform: method(
                    obs,
                    dtype=value,
                    ttype=ttype,
                ),
            ))
        calls.append((
            "image.chisq(obs,dtype={})".format(observable),
            lambda method=image_method, value=observable: method(obs, dtype=value),
        ))

    obs_method = getattr(obs, "chisq", None)
    if obs_method is not None:
        for transform in TRANSFORM_CANDIDATES:
            calls.append((
                "obs.chisq(image,dtype={},ttype={})".format(observable, transform),
                lambda method=obs_method, value=observable, ttype=transform: method(
                    image,
                    dtype=value,
                    ttype=ttype,
                ),
            ))
        calls.append((
            "obs.chisq(image,dtype={})".format(observable),
            lambda method=obs_method, value=observable: method(image, dtype=value),
        ))
    return calls


def measure_observable(image, obs, observable):
    issues = []
    calls = candidate_calls(image, obs, observable)
    if not calls:
        return {
            "observable": observable,
            "status": "unsupported",
            "reduced_chi_squared": None,
            "api_path": None,
            "issues": ["Neither the image nor observation object exposes a chisq method."],
        }

    for api_path, call in calls:
        try:
            value = float(call())
            if not math.isfinite(value) or value < 0:
                issues.append("{} returned non-finite or negative value {!r}".format(api_path, value))
                continue
            return {
                "observable": observable,
                "status": "success",
                "reduced_chi_squared": value,
                "api_path": api_path,
                "issues": issues,
            }
        except Exception as exc:
            issues.append("{}: {}: {}".format(api_path, type(exc).__name__, exc))

    status = "unsupported" if all(
        "ValueError" in issue or "TypeError" in issue or "AttributeError" in issue
        for issue in issues
    ) else "error"
    return {
        "observable": observable,
        "status": status,
        "reduced_chi_squared": None,
        "api_path": None,
        "issues": issues,
    }


def analyze(image_path, bands, observables):
    image, image_loader = load_image(image_path)
    band_reports = []
    requested_count = 0
    successful_count = 0

    for band_id, uvfits_path in bands:
        obs, obs_loader = load_uvfits(uvfits_path)
        results = []
        for observable in observables:
            requested_count += 1
            result = measure_observable(image, obs, observable)
            if result["status"] == "success":
                successful_count += 1
            results.append(result)

        row_count = len(getattr(obs, "data"))
        band_reports.append({
            "band_id": band_id,
            "uvfits": file_identity(uvfits_path),
            "row_count": int(row_count),
            "observables": results,
            "loaders": {
                "image": image_loader,
                "observation": obs_loader,
            },
        })

    failed_count = requested_count - successful_count
    if successful_count == requested_count:
        status = "complete"
    elif successful_count > 0:
        status = "partial"
    else:
        status = "failed"

    for report in band_reports:
        report.pop("loaders", None)

    return {
        "report_version": 1,
        "status": status,
        "method": {
            "method_id": METHOD_ID,
            "library": "ehtim",
            "declared_version": pkg_resources.get_distribution("ehtim").version,
            "transform_type": "first successful of nfft, fast, direct, or library default",
            "observables": list(observables),
        },
        "image": file_identity(image_path),
        "bands": band_reports,
        "summary": {
            "requested_count": requested_count,
            "successful_count": successful_count,
            "failed_count": failed_count,
        },
        "limitations": [
            "The reported values use the public ehtim 1.1.0 chisq API and inherit its observable definitions, data selection, uncertainty handling, and transform implementation.",
            "This diagnostic does not yet reproduce the exact data-term schedule or self-calibration state at every iteration of the published pipeline.",
            "Reduced chi-squared values are not interpreted as an absolute acceptance verdict until observable-specific reviewed thresholds and degrees-of-freedom assumptions are registered.",
            "Low and high bands are measured separately; no cross-band covariance model is included.",
            "A successful image-domain fit does not uniquely identify the source physics."
        ],
    }


def parse_band(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("Band must use ID=PATH")
    band_id, path = value.split("=", 1)
    if not band_id or not path:
        raise argparse.ArgumentTypeError("Band must use non-empty ID=PATH")
    return band_id, Path(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--band", action="append", type=parse_band, required=True)
    parser.add_argument("--observable", action="append", choices=DEFAULT_OBSERVABLES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    observables = tuple(args.observable or DEFAULT_OBSERVABLES)
    report = analyze(args.image, args.band, observables)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] in {"complete", "partial"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
