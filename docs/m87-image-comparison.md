# M87 Image Comparison Contracts

## Purpose

Exact FITS hashes identify a specific execution result, but scientific reproduction should not silently assume universal bitwise determinism across runners and numerical execution contexts.

Vajra therefore separates three comparison layers:

1. **execution identity** — exact FITS and canonical-pixel SHA-256;
2. **paper-derived morphology** — diameter, fractional width, and circularity;
3. **cross-run semantic stability** — pixel similarity and morphology deltas across historical executions.

These layers support the `REC` claim only. They do not establish the full physical interpretation of M87*.

## Primary sources

- Event Horizon Telescope Collaboration, Paper IV: `https://arxiv.org/abs/1906.11241`
- Event Horizon Telescope Collaboration, Paper VI: `https://arxiv.org/abs/1906.11243`

Paper VI Section 7 describes image-domain feature extraction based on:

- interpolation to a `0.5 μas` pixel grid;
- iterative center selection that minimizes the dispersion of radial peak radii;
- a `2 μas` Gaussian blur for center identification in Case B;
- measurement of diameter and radial FWHM from the unblurred image;
- fractional width as mean radial FWHM divided by mean diameter;
- circularity as the standard deviation of orientation-dependent diameters divided by mean diameter.

## Paper-derived morphology contract

Contract:

`cases/m87-black-hole/m87-image-comparison-contract.json`

Implementation:

`scripts/analyze_m87_eht_features.py`

Comparator:

`scripts/compare_m87_image_features.py`

Version `0.1` checks:

| Metric | Comparator |
|---|---:|
| Mean ring diameter | `38–44 μas` |
| Fractional width | `≤ 0.5` |
| Circularity fractional spread | `≤ 0.1` |

These ranges are descriptive values derived from Paper VI discussions. They are not official EHT acceptance thresholds for a single April 11 fiducial reconstruction.

## Verified morphology result

Workflow run: `30219587273`

Artifact digest:

`sha256:f1ade0ce48a5677c73254a17a5d69cf7afbbf9488272b2a8ab2ba8dbec1fe66c`

Both byte-identical executions within that workflow produced the same feature values:

| Metric | Observed |
|---|---:|
| Mean diameter | `41.0708 μas` |
| Mean radial FWHM | `15.5825 μas` |
| Fractional width | `0.37941` |
| Circularity fractional spread | `0.03289` |
| Valid azimuth profiles | `360 / 360` |

All required paper-derived comparators passed.

Persisted result:

`cases/m87-black-hole/m87-eht-paper-morphology-run-30219587273.json`

## Cross-run drift discovery

The earlier Docker/Podman execution family produced:

- FITS SHA-256: `70db37ed8661c6354976f071d4911f77f106fc5f99bcdc0d66a8d2a2ffff16ad`
- canonical-pixel SHA-256: `432f97dbc5ba73f6dfb54be6a948911f8c3690c2e28f7b690979038c369ac6c2`

A later workflow using the same OCI image, inputs, and pipeline produced:

- FITS SHA-256: `f161737292487ddc96a042f7eebacdc91a1f0ac1206c532ee75042af719eefdb`
- canonical-pixel SHA-256: `340b629a40a0e222c40a937ff517a442395541f9f78962d0b6c65356c87cf99e`

Universal bitwise determinism is therefore not established.

Possible causes include host CPU features, numerical-library execution, scheduling, or undeclared pipeline randomness. The current evidence does not identify the cause.

## Cross-run semantic stability contract

Contract:

`cases/m87-black-hole/m87-cross-run-stability-contract.json`

Workflow run:

`30219938594`

Artifact digest:

`sha256:a1789cb268b5c259dace78f8e3297e189960cf4973232f87842fac2f2d438e29`

The workflow downloaded both historical Actions artifacts and independently recalculated their morphology in the verified scientific OCI image.

Observed cross-run comparison:

| Metric | Observed | Limit |
|---|---:|---:|
| Pixel correlation | `0.9999496` | `≥ 0.999` |
| Relative L1 difference | `0.009165` | `≤ 0.02` |
| Relative L2 difference | `0.009147` | `≤ 0.02` |
| Diameter absolute delta | `0.0597 μas` | `≤ 1.0 μas` |
| FWHM absolute delta | `0.0200 μas` | `≤ 1.0 μas` |
| Fractional-width delta | `0.00104` | `≤ 0.02` |
| Circularity delta | `0.00252` | `≤ 0.02` |

All comparators passed.

Persisted report:

`cases/m87-black-hole/m87-cross-run-stability-report.json`

## Evidence interpretation

The `REC` claim remains `supported / S3` because:

- the official pipeline was executed from pinned data and code;
- multiple executions completed successfully;
- exact outputs were repeatable inside execution families;
- Docker and Podman reproduced the same execution-family output;
- a later numerically different output passed the Paper VI-derived morphology contract;
- two historical outputs passed an explicit cross-run semantic stability contract.

The claim is not promoted to `S4` because:

- the feature extractor is a Vajra implementation, not official EHT analysis code;
- the stability limits are engineering-derived, not independently reviewed;
- the runs use the same dataset, pipeline, OCI image, and GitHub-hosted infrastructure class;
- no independent operator or independent scientific method has confirmed the result.

## Remaining work

1. independent review of the feature extractor and thresholds;
2. reproduction on independently controlled infrastructure;
3. investigation of the cross-run numerical drift source;
4. alternate CPU architecture or numerical-library execution;
5. visibility-domain and closure-quantity comparison;
6. machine-readable falsification criteria for competing hypotheses.
