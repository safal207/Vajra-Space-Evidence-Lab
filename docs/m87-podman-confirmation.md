# M87 Podman Runtime Confirmation

## Result

The official April 11, 2017 M87 `eht-imaging` reconstruction was executed through Podman after the earlier Docker reproduction, using the same immutable OCI image digest, pinned UVFITS inputs, pinned official pipeline, and deterministic environment variables.

- Workflow run: `30218457488`
- Runtime: `podman`
- OCI image: `ghcr.io/safal207/vajra-m87-ehtim@sha256:a295853ec4de8ac44523c342e008b0d02b28a3f11aa213e0b777013829db2af3`
- FITS SHA-256: `70db37ed8661c6354976f071d4911f77f106fc5f99bcdc0d66a8d2a2ffff16ad`
- Canonical-pixel SHA-256: `432f97dbc5ba73f6dfb54be6a948911f8c3690c2e28f7b690979038c369ac6c2`
- Podman attestation SHA-256: `9ccc119added4dae0a02af64d3a18e20d018ccbf432fc7b2b2efcdd357d935a1`
- Actions artifact digest: `sha256:90e710f117bd4bb10896b6d8f84c5de9f171118afce0b5dc873a69917ce183ac`

The Podman output matched the prior Docker output exactly at both the FITS-byte and normalized-pixel levels.

## Runtime conformance checks

Before scientific execution, the workflow ran adversarial probes and verified:

1. network access was disabled;
2. the container root filesystem was read-only;
3. effective Linux capabilities were zero;
4. the declared persistent workspace was writable;
5. the configured host timeout terminated a sleeping container.

Podman may provide ephemeral writable tmpfs locations such as `/tmp`. These are runtime scratch surfaces and are not persistent host mounts. The verified persistent host write surface is the declared workspace.

## Evidence classification

This result strengthens the `REC` claim that the ring-like image is reproducible under the declared pipeline and parameters. The claim remains `S3`, not `S4`, because:

- the same OCI image was used;
- the same GitHub-hosted infrastructure class was used;
- the same dataset and pipeline were used;
- no independent operator was involved;
- no independent scientific method was used.

The result is therefore a **runtime-diverse exact confirmation**, not independent scientific confirmation.

## Repository objects

- Executable manifest: `cases/m87-black-hole/m87-ehtim-podman-manifest.json`
- Persisted result: `cases/m87-black-hole/m87-ehtim-podman-confirmation.json`
- Evidence object: `cases/m87-black-hole/evidence-ehtim-podman-runtime-confirmation.json`
- Workflow: `.github/workflows/reproduce-m87-podman.yml`
