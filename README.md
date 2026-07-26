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

## Verified M87 environment checkpoint

The official April 11 data, official imaging pipeline, exact scientific environment, and OCI image are now pinned:

- environment lock: `containers/m87-ehtim/explicit-linux-64.txt`
- environment lock SHA-256: `099067a3cc02fb6cb6e556ada2f9ebeb0d6d9e173e2c61aac3e6b13c0d4527c7`
- OCI image: `ghcr.io/safal207/vajra-m87-ehtim@sha256:ced397b05da668df2d07c28ecf8139dde719e9c5f0f7551857d3b63a41076ee5`
- platform: `linux/amd64`
- upstream `eht-imaging 1.1.0` commit: `22ae35f307921a4d423aa69f6aed6e93a74ecbc0`
- audited Python 3 compatibility patch SHA-256: `7b432916770f1e45108329aff59b4200e148b864e564ab669a5a841402e7d167`

GitHub Actions independently built and pushed the image, pulled it by digest, imported `ehtim 1.1.0`, and started the official M87 pipeline help path successfully.

See [`docs/m87-oci-environment.md`](docs/m87-oci-environment.md) for the environment identity, compatibility patch, verification chain, and remaining scientific limitations.

The scientific reconstruction remains blocked until the expected FITS output and quantitative comparison contract are established.

## Immediate execution order

1. Charter and non-goals
2. Core JSON schemas
3. Evidence-level rules S0–S5
4. Evidence Card validator and renderer
5. M87* reference case
6. CI validation
