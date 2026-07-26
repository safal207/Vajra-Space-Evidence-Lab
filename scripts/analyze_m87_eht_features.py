from __future__ import division, print_function

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.ndimage import gaussian_filter, map_coordinates, zoom


METHOD_ID = "eht-paper-vi-section-7-case-b-derived-v0.1"
TARGET_PIXEL_SCALE_UAS = 0.5
SMOOTHING_FWHM_UAS = 2.0
AZIMUTH_SAMPLES = 360
RADIAL_STEP_UAS = 0.25
MINIMUM_PEAK_RADIUS_UAS = 5.0
MAXIMUM_PROFILE_RADIUS_UAS = 50.0


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
        header = hdu.header
    if image.ndim != 2:
        raise ValueError("Expected a 2-D FITS image, got shape {}".format(image.shape))
    if not np.isfinite(image).any():
        raise ValueError("FITS image has no finite pixels")
    image = image.copy()
    image[~np.isfinite(image)] = 0.0
    cdelt = header.get("CDELT1") or header.get("CD1_1")
    if cdelt is None:
        raise ValueError("FITS image has no CDELT1 or CD1_1 pixel scale")
    pixel_scale_uas = abs(float(cdelt)) * 3600.0 * 1.0e6
    return image, pixel_scale_uas


def resample_linear(image, source_pixel_scale_uas, target_pixel_scale_uas):
    factor = float(source_pixel_scale_uas) / float(target_pixel_scale_uas)
    if factor <= 0:
        raise ValueError("Invalid resampling factor")
    resampled = zoom(
        image,
        zoom=factor,
        order=1,
        mode="nearest",
        prefilter=False,
    )
    return resampled, factor


def positive_centroid(image):
    positive = np.clip(image, 0.0, None)
    total = float(positive.sum())
    if total <= 0:
        return ((image.shape[1] - 1) / 2.0, (image.shape[0] - 1) / 2.0)
    yy, xx = np.indices(image.shape, dtype=float)
    return (
        float((positive * xx).sum() / total),
        float((positive * yy).sum() / total),
    )


def sample_profiles(image, center_x, center_y, angles, radii_pixels):
    xx = center_x + np.cos(angles)[:, None] * radii_pixels[None, :]
    yy = center_y + np.sin(angles)[:, None] * radii_pixels[None, :]
    coordinates = np.vstack([yy.ravel(), xx.ravel()])
    values = map_coordinates(
        image,
        coordinates,
        order=1,
        mode="nearest",
        prefilter=False,
    )
    return values.reshape((len(angles), len(radii_pixels)))


def peak_radii_for_center(
    image,
    center_x,
    center_y,
    angles,
    radii_uas,
    pixel_scale_uas,
):
    radii_pixels = radii_uas / pixel_scale_uas
    profiles = sample_profiles(image, center_x, center_y, angles, radii_pixels)
    minimum_index = int(np.searchsorted(radii_uas, MINIMUM_PEAK_RADIUS_UAS))
    offsets = np.argmax(profiles[:, minimum_index:], axis=1)
    indices = offsets + minimum_index
    return radii_uas[indices]


def center_objective(image, center_x, center_y, angles, radii_uas, pixel_scale_uas):
    margin = MAXIMUM_PROFILE_RADIUS_UAS / pixel_scale_uas
    if (
        center_x < margin
        or center_y < margin
        or center_x > image.shape[1] - 1 - margin
        or center_y > image.shape[0] - 1 - margin
    ):
        return float("inf")
    peak_radii = peak_radii_for_center(
        image,
        center_x,
        center_y,
        angles,
        radii_uas,
        pixel_scale_uas,
    )
    return float(np.std(peak_radii))


def find_ring_center(smoothed, angles, radii_uas, pixel_scale_uas):
    current_x, current_y = positive_centroid(smoothed)
    initial_x, initial_y = current_x, current_y
    history = []

    for step_pixels in (4.0, 2.0, 1.0, 0.5):
        best_x = current_x
        best_y = current_y
        best_score = center_objective(
            smoothed,
            best_x,
            best_y,
            angles,
            radii_uas,
            pixel_scale_uas,
        )
        for dy_multiplier in (-2, -1, 0, 1, 2):
            for dx_multiplier in (-2, -1, 0, 1, 2):
                candidate_x = current_x + dx_multiplier * step_pixels
                candidate_y = current_y + dy_multiplier * step_pixels
                score = center_objective(
                    smoothed,
                    candidate_x,
                    candidate_y,
                    angles,
                    radii_uas,
                    pixel_scale_uas,
                )
                candidate_key = (score, candidate_y, candidate_x)
                best_key = (best_score, best_y, best_x)
                if candidate_key < best_key:
                    best_x = candidate_x
                    best_y = candidate_y
                    best_score = score
        current_x = best_x
        current_y = best_y
        history.append({
            "step_pixels": step_pixels,
            "step_microarcseconds": step_pixels * pixel_scale_uas,
            "center_x_pixels": current_x,
            "center_y_pixels": current_y,
            "peak_radius_standard_deviation_microarcseconds": best_score,
        })

    return {
        "initial_centroid_x_pixels": initial_x,
        "initial_centroid_y_pixels": initial_y,
        "center_x_pixels": current_x,
        "center_y_pixels": current_y,
        "center_x_microarcseconds_from_image_origin": current_x * pixel_scale_uas,
        "center_y_microarcseconds_from_image_origin": current_y * pixel_scale_uas,
        "search_history": history,
    }


def interpolate_crossing(radius_a, value_a, radius_b, value_b, target):
    if value_b == value_a:
        return 0.5 * (radius_a + radius_b)
    fraction = (target - value_a) / (value_b - value_a)
    fraction = max(0.0, min(1.0, float(fraction)))
    return radius_a + fraction * (radius_b - radius_a)


def profile_fwhm(radii_uas, profile, peak_index):
    peak_value = float(profile[peak_index])
    if peak_value <= 0:
        return None
    half = peak_value / 2.0

    inner_index = None
    for index in range(peak_index - 1, -1, -1):
        if profile[index] <= half:
            inner_index = index
            break
    outer_index = None
    for index in range(peak_index + 1, len(profile)):
        if profile[index] <= half:
            outer_index = index
            break
    if inner_index is None or outer_index is None:
        return None

    inner_radius = interpolate_crossing(
        float(radii_uas[inner_index]),
        float(profile[inner_index]),
        float(radii_uas[inner_index + 1]),
        float(profile[inner_index + 1]),
        half,
    )
    outer_radius = interpolate_crossing(
        float(radii_uas[outer_index - 1]),
        float(profile[outer_index - 1]),
        float(radii_uas[outer_index]),
        float(profile[outer_index]),
        half,
    )
    width = outer_radius - inner_radius
    return width if width >= 0 else None


def extract_features(image, pixel_scale_uas):
    resampled, zoom_factor = resample_linear(
        image,
        pixel_scale_uas,
        TARGET_PIXEL_SCALE_UAS,
    )
    effective_scale = pixel_scale_uas / zoom_factor
    sigma_pixels = (
        SMOOTHING_FWHM_UAS
        / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        / effective_scale
    )
    smoothed = gaussian_filter(resampled, sigma=sigma_pixels, mode="nearest")

    angles = np.linspace(0.0, 2.0 * math.pi, AZIMUTH_SAMPLES, endpoint=False)
    radii_uas = np.arange(
        0.0,
        MAXIMUM_PROFILE_RADIUS_UAS + RADIAL_STEP_UAS / 2.0,
        RADIAL_STEP_UAS,
    )

    center = find_ring_center(
        smoothed,
        angles,
        radii_uas,
        effective_scale,
    )
    center_x = center["center_x_pixels"]
    center_y = center["center_y_pixels"]

    profiles = sample_profiles(
        resampled,
        center_x,
        center_y,
        angles,
        radii_uas / effective_scale,
    )
    minimum_index = int(np.searchsorted(radii_uas, MINIMUM_PEAK_RADIUS_UAS))
    peak_indices = np.argmax(profiles[:, minimum_index:], axis=1) + minimum_index
    peak_radii_uas = radii_uas[peak_indices]
    diameters_uas = 2.0 * peak_radii_uas

    widths = []
    for profile, peak_index in zip(profiles, peak_indices):
        width = profile_fwhm(radii_uas, profile, int(peak_index))
        if width is not None and math.isfinite(width):
            widths.append(float(width))

    mean_diameter = float(np.mean(diameters_uas))
    diameter_std = float(np.std(diameters_uas))
    mean_width = None if not widths else float(np.mean(widths))
    width_std = None if not widths else float(np.std(widths))
    fractional_width = (
        None
        if mean_width is None or mean_diameter == 0
        else mean_width / mean_diameter
    )

    center["center_x_source_pixels"] = center_x / zoom_factor
    center["center_y_source_pixels"] = center_y / zoom_factor

    return {
        "method": {
            "method_id": METHOD_ID,
            "target_pixel_scale_microarcseconds": TARGET_PIXEL_SCALE_UAS,
            "effective_pixel_scale_microarcseconds": effective_scale,
            "interpolation": "linear",
            "center_smoothing_fwhm_microarcseconds": SMOOTHING_FWHM_UAS,
            "center_estimator": "iterative grid minimization of azimuthal peak-radius standard deviation",
            "measurement_image": "unblurred_resampled",
            "azimuth_samples": AZIMUTH_SAMPLES,
            "radial_step_microarcseconds": RADIAL_STEP_UAS,
            "minimum_peak_radius_microarcseconds": MINIMUM_PEAK_RADIUS_UAS,
            "maximum_profile_radius_microarcseconds": MAXIMUM_PROFILE_RADIUS_UAS,
        },
        "resampling": {
            "source_shape": list(image.shape),
            "resampled_shape": list(resampled.shape),
            "source_pixel_scale_microarcseconds": pixel_scale_uas,
            "zoom_factor": zoom_factor,
        },
        "center": center,
        "metrics": {
            "mean_diameter_microarcseconds": mean_diameter,
            "diameter_standard_deviation_microarcseconds": diameter_std,
            "circularity_fractional_spread": (
                None if mean_diameter == 0 else diameter_std / mean_diameter
            ),
            "mean_fwhm_microarcseconds": mean_width,
            "fwhm_standard_deviation_microarcseconds": width_std,
            "fractional_width": fractional_width,
            "azimuth_profile_count": int(len(angles)),
            "valid_width_profile_count": int(len(widths)),
            "minimum_peak_radius_microarcseconds": float(np.min(peak_radii_uas)),
            "maximum_peak_radius_microarcseconds": float(np.max(peak_radii_uas)),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fits", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    image, pixel_scale_uas = read_image(args.fits)
    report = {
        "report_version": 1,
        "scope": "Paper-derived M87 image-domain feature extraction; not official EHT analysis code.",
        "input": {
            "path": args.fits.name,
            "sha256": sha256_file(args.fits),
            "size_bytes": args.fits.stat().st_size,
        },
    }
    report.update(extract_features(image, pixel_scale_uas))
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
