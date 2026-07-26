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

The official April 11 data, official imaging pipeline, exact scientific environment, and generated output are now pinned:

- environment lock: `containers/m87-ehtim/explicit-linux-64.txt`
- environment lock SHA-256: `e4f061d38ccc642dd55cf4e4d100319749e632b001c1b0c5c0ceb5bf10061448`
- OCI image: `ghcr.io/safal207/vajra-m87-ehtim@sha256:a295853ec4de8ac44523c342e008b0d02b28a3f11aa213e0b777013829db2af3`
- platform: `linux/amd64`
- upstream `eht-imaging 1.1.0` commit: `22ae35f307921a4d423aa69f6aed6e93a74ecbc0`
- audited Python 3 compatibility patch SHA-256: `7b432916770f1e45108329aff59b4200e148b864e564ab669a5a841402e7d167`
- repeated FITS SHA-256: `70db37ed8661c6354976f071d4911f77f106fc5f99bcdc0d66a8d2a2ffff16ad`
- repeated canonical-pixel SHA-256: `432f97dbc5ba73f6dfb54be6a948911f8c3690c2e28f7b690979038c369ac6c2`

GitHub Actions executed the official April 11 M87 reconstruction twice with container networking disabled, a read-only root filesystem, dropped capabilities, and the same digest-addressed OCI environment. Both generated FITS files matched byte-for-byte and all bootstrap diagnostic values matched exactly.

See:

- [`docs/m87-oci-environment.md`](docs/m87-oci-environment.md)
- [`cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json`](cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json)
- [`cases/m87-black-hole/eht-imaging-reproduction-plan.json`](cases/m87-black-hole/eht-imaging-reproduction-plan.json)

The reproduction status is **partial**, not complete. Independent execution, reviewed scientific image comparators, and cross-runtime stability limits remain open.

## Immediate execution order

1. Charter and non-goals
2. Core JSON schemas
3. Evidence-level rules S0–S5
4. Evidence Card validator and renderer
5. M87* reference case
6. CI validation
