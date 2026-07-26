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

It is **not S4**. Docker and Podman used the same OCI image, dataset, pipeline, and GitHub-hosted infrastructure class. Runtime diversity is not an independent operator, independent dataset, or independent scientific method.

The broader physical interpretation of M87\* remains separate from this reconstruction claim.

## Reference files

- [`docs/m87-oci-environment.md`](docs/m87-oci-environment.md)
- [`docs/m87-podman-confirmation.md`](docs/m87-podman-confirmation.md)
- [`docs/attestation-signatures.md`](docs/attestation-signatures.md)
- [`cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json`](cases/m87-black-hole/m87-ehtim-bootstrap-reproduction.json)
- [`cases/m87-black-hole/m87-ehtim-podman-confirmation.json`](cases/m87-black-hole/m87-ehtim-podman-confirmation.json)
- [`cases/m87-black-hole/m87-ehtim-podman-manifest.json`](cases/m87-black-hole/m87-ehtim-podman-manifest.json)
- [`cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json`](cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json)
- [`trust/signer-registry.json`](trust/signer-registry.json)
- [`cases/m87-black-hole/evidence-bundle.json`](cases/m87-black-hole/evidence-bundle.json)

## Immediate execution order

1. Independent operator or external-infrastructure reproduction
2. Reviewed scientific image-comparison contract
3. Alternate platform or numerical-library confirmation
4. Independent trust anchoring or transparency log
5. Materially independent confirmation objects
6. Complete M87\* Evidence Card
7. Space-safety reference cases
