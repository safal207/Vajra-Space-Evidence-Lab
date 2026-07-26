from __future__ import division, print_function

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from astropy.io import fits


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_pixel_hash(array):
    canonical = np.asarray(array, dtype="<f8").copy(order="C")
    canonical[~np.isfinite(canonical)] = 0.0
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def radial_metrics(image, cx, cy, pixel_scale_uas):
    yy, xx = np.indices(image.shape, dtype=float)
    radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    positive = np.clip(image, 0.0, None)

    bin_width = 0.25
    max_radius = float(radius.max())
    edges = np.arange(0.0, max_radius + bin_width, bin_width)
    if len(edges) < 3:
        return {
            "peak_radius_pixels": None,
            "diameter_microarcseconds": None,
            "fwhm_pixels": None,
            "fwhm_microarcseconds": None,
        }

    sums, _ = np.histogram(radius.ravel(), bins=edges, weights=positive.ravel())
    counts, _ = np.histogram(radius.ravel(), bins=edges)
    profile = sums / np.maximum(counts, 1)
    centers = 0.5 * (edges[:-1] + edges[1:])

    peak_index = int(np.argmax(profile))
    peak_value = float(profile[peak_index])
    peak_radius = float(centers[peak_index])
    half = peak_value / 2.0
    above = np.where(profile >= half)[0]
    if len(above):
        fwhm = float(edges[above[-1] + 1] - edges[above[0]])
    else:
        fwhm = None

    return {
        "peak_radius_pixels": peak_radius,
        "diameter_microarcseconds": 2.0 * peak_radius * pixel_scale_uas,
        "fwhm_pixels": fwhm,
        "fwhm_microarcseconds": None if fwhm is None else fwhm * pixel_scale_uas,
    }


def analyze(path):
    with fits.open(str(path), memmap=False) as hdul:
        hdu = next(item for item in hdul if item.data is not None)
        image = np.asarray(hdu.data, dtype=float).squeeze()
        header = hdu.header

    if image.ndim != 2:
        raise ValueError("Expected a 2-D FITS image after squeeze, got shape {}".format(image.shape))

    finite_mask = np.isfinite(image)
    finite_pixel_count = int(finite_mask.sum())
    if finite_pixel_count == 0:
        raise ValueError("FITS image has no finite pixels")

    image = image.copy()
    image[~finite_mask] = 0.0
    positive = np.clip(image, 0.0, None)
    weight_sum = float(positive.sum())
    yy, xx = np.indices(image.shape, dtype=float)

    if weight_sum > 0:
        cx = float((positive * xx).sum() / weight_sum)
        cy = float((positive * yy).sum() / weight_sum)
    else:
        cx = (image.shape[1] - 1) / 2.0
        cy = (image.shape[0] - 1) / 2.0

    dx = xx - cx
    dy = yy - cy
    if weight_sum > 0:
        mxx = float((positive * dx * dx).sum() / weight_sum)
        myy = float((positive * dy * dy).sum() / weight_sum)
        mxy = float((positive * dx * dy).sum() / weight_sum)
        orientation_deg = 0.5 * math.degrees(math.atan2(2.0 * mxy, mxx - myy))
    else:
        orientation_deg = None

    rotated = np.rot90(image, 2)
    asymmetry_denominator = float(np.abs(image).sum())
    asymmetry = (
        None
        if asymmetry_denominator == 0
        else float(np.abs(image - rotated).sum() / asymmetry_denominator)
    )

    cdelt = header.get("CDELT1") or header.get("CD1_1")
    if cdelt:
        pixel_scale_uas = abs(float(cdelt)) * 3600.0 * 1.0e6
        pixel_scale_source = "fits_header"
    else:
        pixel_scale_uas = 128.0 / float(image.shape[1])
        pixel_scale_source = "fiducial_fov_fallback"

    metrics = radial_metrics(image, cx, cy, pixel_scale_uas)
    metrics.update(
        {
            "file_sha256": sha256_file(path),
            "canonical_pixel_sha256": canonical_pixel_hash(image),
            "shape": list(image.shape),
            "dtype_normalized": "float64-little-endian",
            "finite_pixel_count": finite_pixel_count,
            "minimum": float(image.min()),
            "maximum": float(image.max()),
            "sum": float(image.sum()),
            "absolute_sum": float(np.abs(image).sum()),
            "positive_sum": weight_sum,
            "centroid_x_pixels": cx,
            "centroid_y_pixels": cy,
            "orientation_degrees_diagnostic": orientation_deg,
            "rotational_asymmetry_l1": asymmetry,
            "pixel_scale_microarcseconds": pixel_scale_uas,
            "pixel_scale_source": pixel_scale_source,
        }
    )
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fits", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = {
        "report_version": 1,
        "metric_scope": "bootstrap image diagnostics; not yet the independently reviewed EHT ring measurement contract",
        "fits_path": args.fits.name,
        "metrics": analyze(args.fits),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
