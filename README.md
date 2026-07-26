# Vajra Space Evidence Lab

Independent, reproducible evidence infrastructure for space science and space safety.

## Mission

Vajra Space Evidence Lab separates:

- **OBS** — direct observation
- **REC** — reconstructed result
- **INF** — scientific inference
- **SIM** — simulation
- **PRED** — prediction
- **SPEC** — speculative hypothesis

The project does not appoint truth by authority. It exposes provenance, transformations,
assumptions, uncertainty, independent confirmations, competing explanations, and reproducibility.

## First milestone

Build a validated **Evidence Card** format and publish the first reference case for **M87\***.

## Verified M87 environment

The official April 11 data, official imaging pipeline, and scientific execution environment are pinned:

- environment lock: `containers/m87-ehtim/explicit-linux-64.txt`
- environment lock SHA-256: `e4f061d38ccc642dd55cf4e4d100319749e632b001c1b0c5c0ceb5bf10061448`
- OCI image: `ghcr.io/safal207/vajra-m87-ehtim@sha256:a295853ec4de8ac44523c342e008b0d02b28a3f11aa213e0b777013829db2af3`
- platform: `linux/amd64`
- upstream `eht-imaging 1.1.0` commit: `22ae35f307921a4d423aa69f6aed6e93a74ecbc0`
- audited Python 3 compatibility patch SHA-256: `7b432916770f1e45108329aff59b4200e148b864e564ab669a5a841402e7d167`

## First exact execution family

GitHub Actions executed the official reconstruction twice through Docker. Both outputs matched byte-for-byte:

- FITS SHA-256: `70db37ed8661c6354976f071d4911f77f106fc5f99bcdc0d66a8d2a2ffff16ad`
- canonical-pixel SHA-256: `432f97dbc5ba73f6dfb54be6a948911f8c3690c2e28f7b690979038c369ac6c2`
- Docker artifact digest: `sha256:426bf04167f25e4974186bd045815ed96aaad1efd4145ed294955aa416ad4f80`

A separate Podman workflow then:

1. verified disabled networking;
2. verified a read-only container root filesystem;
3. verified zero effective Linux capabilities;
4. verified the declared persistent workspace;
5. verified timeout termination;
6. reproduced the exact same FITS and canonical pixels.

Podman artifact digest:

`sha256:90e710f117bd4bb10896b6d8f84c5de9f171118afce0b5dc873a69917ce183ac`

The exact hash identifies this execution family. It is not treated as a universal scientific output hash.

## Paper VI-derived morphology

A later workflow using the same OCI image, data, and pipeline produced a numerically different FITS file:

- FITS SHA-256: `f161737292487ddc96a042f7eebacdc91a1f0ac1206c532ee75042af719eefdb`
- canonical-pixel SHA-256: `340b629a40a0e222c40a937ff517a442395541f9f78962d0b6c65356c87cf99e`

This disproves universal bitwise determinism across GitHub-hosted workflow executions.

Vajra implemented a transparent image-domain feature extractor derived from the published Paper VI Section 7 method:

- interpolation to `0.5 μas` pixels;
- `2 μas` Gaussian smoothing for ring-center selection;
- iterative minimization of radial-peak dispersion;
- diameter and radial FWHM measured on the unblurred resampled image;
- 360 azimuthal profiles.

Observed morphology:

| Metric | Result |
|---|---:|
| Mean diameter | `41.0708 μas` |
| Mean radial FWHM | `15.5825 μas` |
| Fractional width | `0.37941` |
| Circularity fractional spread | `0.03289` |

The paper-derived diameter, width, and circularity comparators all passed.

This is a Vajra implementation derived from published prose, not official EHT analysis code.

## Cross-run semantic stability

A dedicated workflow downloaded two historical reproduction artifacts and recalculated their morphology inside the verified scientific OCI image.

- workflow run: `30219938594`
- artifact digest: `sha256:a1789cb268b5c259dace78f8e3297e189960cf4973232f87842fac2f2d438e29`

Observed cross-run stability:

| Metric | Result |
|---|---:|
| Pixel correlation | `0.9999496` |
| Relative L1 difference | `0.009165` |
| Relative L2 difference | `0.009147` |
| Diameter delta | `0.0597 μas` |
| FWHM delta | `0.0200 μas` |
| Fractional-width delta | `0.00104` |
| Circularity delta | `0.00252` |

All seven engineering-derived stability comparators passed.

Therefore Vajra separates:

```text
exact hash → identity of one execution family
morphology contract → portable scientific reconstruction result
```

The source of the small cross-run numerical drift is still unknown.

## Public attestation signature

The Podman reproduction attestation is publicly verifiable with Ed25519:

- signed attestation: `cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json`
- signed file SHA-256: `b13106e43dabab4c0051cf7dc1780aed46e8656aa7b18ad3d03332ce98516061`
- key ID: `vajra-m87-podman-ceremony-2026-07-26`
- public-key fingerprint: `sha256:7b2b0152eb08c728e7d11e519703aeb300cdb9cc1f83fdeef5f5bb00ffff28a1`
- key status: `retired`
- signer registry: `trust/signer-registry.json`
- registry SHA-256: `06e305777985b97d09083dfa8c0579f285b59a503e9dcbdbbd239bc31e2fbba7`

Verify without private material:

```bash
python scripts/ed25519_attestation.py verify \
  cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json \
  --registry trust/signer-registry.json
```

The signature proves integrity and signer-key control. It does not independently prove scientific truth, trusted time, or signer independence.

## Evidence status

The machine-readable `REC` claim — that a ring-like image can be reconstructed under the declared pipeline and parameters — is currently:

```text
supported / S3
```

It is **not S4**. The feature extractor and stability limits are not independently reviewed, and the runs use the same dataset, pipeline, OCI image, and GitHub-hosted infrastructure class.

The broader physical interpretation of M87\* remains separate from this reconstruction claim.

## Reference files

- [`docs/m87-oci-environment.md`](docs/m87-oci-environment.md)
- [`docs/m87-podman-confirmation.md`](docs/m87-podman-confirmation.md)
- [`docs/m87-image-comparison.md`](docs/m87-image-comparison.md)
- [`docs/attestation-signatures.md`](docs/attestation-signatures.md)
- [`docs/structured-reports.md`](docs/structured-reports.md)
- [`cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json`](cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json)
- [`cases/m87-black-hole/m87-ehtim-podman-confirmation.json`](cases/m87-black-hole/m87-ehtim-podman-confirmation.json)
- [`cases/m87-black-hole/m87-eht-paper-morphology-run-30219587273.json`](cases/m87-black-hole/m87-eht-paper-morphology-run-30219587273.json)
- [`cases/m87-black-hole/m87-cross-run-stability-report.json`](cases/m87-black-hole/m87-cross-run-stability-report.json)
- [`cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json`](cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json)
- [`trust/signer-registry.json`](trust/signer-registry.json)
- [`cases/m87-black-hole/evidence-bundle.json`](cases/m87-black-hole/evidence-bundle.json)

## Immediate execution order

1. Independent review of the Paper VI-derived feature extractor and tolerances
2. Independent operator or external-infrastructure reproduction
3. Investigation of cross-run numerical drift
4. Alternate CPU architecture or numerical-library confirmation
5. Visibility-domain and closure-quantity comparison
6. Independent trust anchoring or transparency log
7. Materially independent confirmation objects
8. Complete M87\* Evidence Card
9. Space-safety reference cases
