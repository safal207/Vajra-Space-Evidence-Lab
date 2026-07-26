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

## Verified M87 reproduction checkpoint

The official April 11 data, official imaging pipeline, exact scientific environment, and generated output are pinned:

- environment lock: `containers/m87-ehtim/explicit-linux-64.txt`
- environment lock SHA-256: `e4f061d38ccc642dd55cf4e4d100319749e632b001c1b0c5c0ceb5bf10061448`
- OCI image: `ghcr.io/safal207/vajra-m87-ehtim@sha256:a295853ec4de8ac44523c342e008b0d02b28a3f11aa213e0b777013829db2af3`
- platform: `linux/amd64`
- upstream `eht-imaging 1.1.0` commit: `22ae35f307921a4d423aa69f6aed6e93a74ecbc0`
- audited Python 3 compatibility patch SHA-256: `7b432916770f1e45108329aff59b4200e148b864e564ab669a5a841402e7d167`
- FITS SHA-256: `70db37ed8661c6354976f071d4911f77f106fc5f99bcdc0d66a8d2a2ffff16ad`
- canonical-pixel SHA-256: `432f97dbc5ba73f6dfb54be6a948911f8c3690c2e28f7b690979038c369ac6c2`

GitHub Actions first executed the official reconstruction twice through Docker. Both generated FITS files matched byte-for-byte and all bootstrap diagnostic values matched exactly.

A separate Podman workflow then:

1. verified disabled networking;
2. verified a read-only container root filesystem;
3. verified zero effective Linux capabilities;
4. verified the declared persistent workspace;
5. verified timeout termination;
6. reproduced the exact same FITS and canonical pixels.

Podman confirmation artifact digest:

`sha256:90e710f117bd4bb10896b6d8f84c5de9f171118afce0b5dc873a69917ce183ac`

## Evidence status

The machine-readable `REC` claim — that a ring-like image can be reconstructed under the declared pipeline and parameters — is currently:

```text
supported / S3
```

It is **not S4**. Docker and Podman used the same OCI image, dataset, pipeline, and GitHub-hosted infrastructure class. Runtime diversity is not an independent operator, independent dataset, or independent scientific method.

The broader physical interpretation of M87\* remains separate from this reconstruction claim.

## Reference files

- [`docs/m87-oci-environment.md`](docs/m87-oci-environment.md)
- [`docs/m87-podman-confirmation.md`](docs/m87-podman-confirmation.md)
- [`cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json`](cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json)
- [`cases/m87-black-hole/m87-ehtim-podman-confirmation.json`](cases/m87-black-hole/m87-ehtim-podman-confirmation.json)
- [`cases/m87-black-hole/m87-ehtim-podman-manifest.json`](cases/m87-black-hole/m87-ehtim-podman-manifest.json)
- [`cases/m87-black-hole/evidence-bundle.json`](cases/m87-black-hole/evidence-bundle.json)

## Immediate execution order

1. Independent operator or external-infrastructure reproduction
2. Reviewed scientific image-comparison contract
3. Publicly verifiable Ed25519 attestations
4. Materially independent confirmation objects
5. Complete M87\* Evidence Card
6. Space-safety reference cases
