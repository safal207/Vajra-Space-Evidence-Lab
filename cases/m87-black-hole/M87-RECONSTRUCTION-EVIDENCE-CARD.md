# M87 Ring-Image Reconstruction Evidence Card

> A ring-like image can be reconstructed from calibrated VLBI measurements under declared algorithms and parameters.

## Verdict

| Field | Value |
|---|---|
| Claim type | `REC` |
| Status | `supported` |
| Declared level | `S3` |
| Calculated level | `S3` |
| Claim version | `4` |

This card assesses only the REC claim that a ring-like image can be reconstructed from the declared calibrated VLBI inputs, code, parameters, and comparison contracts.

## Why this level

- S1: traceable provenance and at least one observation exist.
- S2: data and method are inspectable.
- S3: result reproduced from pinned code, environment, and declared uncertainty.

## Evidence

- **`evidence:m87:ehtim-bootstrap-reproduction`** — `reproduction`; source hash `426bf04167f25e4974186bd045815ed96aaad1efd4145ed294955aa416ad4f80`. The official released April 11 eht-imaging pipeline produced byte-identical FITS and canonical-pixel hashes in two executions inside one pinned linux/amd64 OCI workflow, and Podman later reproduced that exact output. A subsequent GitHub-hosted workflow using the same OCI image, data, and pipeline produced a different FITS and canonical-pixel hash, revealing cross-run numerical or undeclared-randomness drift. Therefore the exact hash identifies this execution family but is not a universal expected output. Independent cross-run evidence must use explicit semantic image and morphology comparators. Independent operator, platform, method, and full physical-interpretation confirmation remain unavailable.
- **`evidence:m87:ehtim-podman-runtime-confirmation`** — `reproduction`; source hash `90e710f117bd4bb10896b6d8f84c5de9f171118afce0b5dc873a69917ce183ac`. The same official April 11 reconstruction produced byte-identical FITS and canonical-pixel hashes through Podman after the Docker reproduction, while network, read-only-root, dropped-capability, timeout, and persistent-workspace controls were exercised. This confirms runtime diversity only; the OCI image, GitHub-hosted infrastructure, dataset, pipeline, and scientific method were not independent.
- **`evidence:m87:paper-derived-morphology-stability`** — `reproduction`; source hash `a1789cb268b5c259dace78f8e3297e189960cf4973232f87842fac2f2d438e29`. Two historical reconstruction artifacts produced different FITS and canonical-pixel hashes under the same OCI image, data, and pipeline, so universal bitwise determinism is not established. A fresh CI workflow independently downloaded both artifacts, re-extracted Paper VI-derived morphology in the verified scientific image, and passed an engineering-derived stability contract: pixel correlation 0.9999496, relative L1/L2 drift below one percent, diameter delta 0.0597 microarcseconds, FWHM delta 0.0200 microarcseconds, fractional-width delta 0.00104, and circularity delta 0.00252. The feature extractor and stability thresholds are Vajra implementations derived from published prose and are not official EHT code or independently reviewed tolerances.

## Reproduction

- Paper-derived morphology contract: `pass`
- Mean diameter: `41.0708 μas`
- Mean radial FWHM: `15.5825 μas`
- Fractional width: `0.37941`
- Circularity fractional spread: `0.03289`
- Cross-run stability: `pass`

## Competing alternatives

- **`claim:m87:calibration-artifact`** — `SPEC` / `not_assessed`: The ring-scale signature is primarily produced by shared calibration error rather than source structure.
- **`claim:m87:imaging-prior-artifact`** — `SPEC` / `not_assessed`: Sparse Fourier coverage and imaging priors force a ring-like reconstruction that is not required by the calibrated observables.
- **`claim:m87:jet-only-morphology`** — `SPEC` / `not_assessed`: The compact structure can be explained by jet-base emission without requiring a black-hole shadow interpretation.
- **`claim:m87:non-kerr-compact-object`** — `SPEC` / `not_assessed`: The central source is an ultracompact object not described by the Kerr black-hole solution.
- **`claim:m87:variability-bias`** — `SPEC` / `not_assessed`: Source variability interacting with Earth-rotation synthesis materially biases the reconstructed static morphology.

## Open requirements

- alternate CPU architecture or numerical-library execution
- byte-for-byte equivalence with the CyVerse DOI endpoint
- independent operator or external-infrastructure reproduction
- independent review of the Paper VI-derived feature extractor and thresholds
- investigation of cross-run numerical drift
- materially independent confirmation objects
- pinned calibration pipeline commits and execution environment
- visibility-domain and closure-quantity comparison

## Limitations

- The card is scoped to the REC reconstruction claim and does not assess the broader Kerr black-hole inference.
- Exact FITS and canonical-pixel hashes vary across workflow execution families despite fixed OCI, data, and code.
- Paper VI-derived feature extraction and cross-run tolerances are Vajra implementations and are not independently reviewed EHT code.
- Docker and Podman runtime diversity does not constitute independent scientific confirmation.
- The Ed25519 signature proves attestation integrity and key control, not scientific truth or trusted time.
