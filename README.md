# Vajra Space Evidence Lab

Independent, reproducible evidence infrastructure for space science and space safety.

## Mission

Vajra separates direct observation (`OBS`), reconstruction (`REC`), scientific inference (`INF`), simulation (`SIM`), prediction (`PRED`), and speculation (`SPEC`). It does not appoint truth by authority; it exposes provenance, transformations, assumptions, uncertainty, alternatives, independent confirmations, and reproducibility.

## Current capabilities

- JSON schemas for claims, evidence, observations, instruments, transformations, assumptions, and bundles.
- Fail-closed validation and deterministic S0–S5 scoring.
- Tamper-evident claim ledger.
- Bundle referential-integrity and content-hash validation.
- Pinned ingestion and SHA-256 inventory of the official EHT M87 calibrated-data Git release.
- Initial M87* evidence graph and explicit competing hypotheses.

## M87* provenance checkpoint

Vajra ingested the official EHT `2019-D01-01` Git release at commit
`27ae76aacb9067a83388395c3826012b97aac371` and calculated SHA-256 hashes for
all 34 release files. The canonical release-tree digest is:

```text
9134b5f261bd6936d9e25547eca722be89b325b587fe22d06ba980b0de31a896
```

This proves which bytes from the pinned official Git release were assessed. It
does **not** yet prove byte-for-byte equivalence with the CyVerse DOI endpoint,
reproduce the calibration pipelines, or reproduce the published image.
Therefore the M87* case remains `S0 / incomplete`.

## First milestone

Publish the first complete, independently reproducible Evidence Card for M87*.

## Run locally

```bash
pip install -e .[dev]
pytest -q
vajra-space validate-bundle cases/m87-black-hole/evidence-bundle.json
```
