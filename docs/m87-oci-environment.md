# M87 `eht-imaging` OCI Environment

## Verified identity

- OCI reference: `ghcr.io/safal207/vajra-m87-ehtim@sha256:ced397b05da668df2d07c28ecf8139dde719e9c5f0f7551857d3b63a41076ee5`
- Platform: `linux/amd64`
- Base image: `mambaorg/micromamba:1-bookworm-slim@sha256:e3797091302382ea841498bc93a7b0a50f7c1448333d5e946d2d1608d0c5f43d`
- Exact Conda lock: `containers/m87-ehtim/explicit-linux-64.txt`
- Lock SHA-256: `099067a3cc02fb6cb6e556ada2f9ebeb0d6d9e173e2c61aac3e6b13c0d4527c7`

## Upstream source

- Repository: `https://github.com/achael/eht-imaging.git`
- Commit: `22ae35f307921a4d423aa69f6aed6e93a74ecbc0`
- Tree SHA-256: `efea21644ef3dc837b878431bf1081c4e7e1570084a690e57cfa2ec0714fe5ef`
- Declared package version: `1.1.0`

## Audited compatibility patch

Upstream `eht-imaging 1.1.0` contains two Python 2 syntax forms in `ehtim/parloop.py` that prevent Python 3 import. Vajra applies one auditable patch that only changes syntax:

- `print 'pool terminated'` → `print('pool terminated')`
- `except Exception, e:` → `except Exception as e:`

Patch path: `containers/m87-ehtim/patches/ehtim-1.1.0-python3-parloop.patch`

Patch SHA-256: `7b432916770f1e45108329aff59b4200e148b864e564ab669a5a841402e7d167`

The patch does not change imaging parameters, numerical algorithms, calibration logic, or scientific outputs by design. This claim still requires output-level confirmation through repeated reconstruction.

## CI verification

GitHub Actions run `30207169122` completed successfully and verified:

1. immutable base-image resolution;
2. deterministic Conda environment solving;
3. exact lock generation;
4. upstream source-tree and patch hashes;
5. GHCR image build and push with SBOM and provenance;
6. pull of the published image by digest;
7. successful import of `ehtim 1.1.0`;
8. successful start of the official M87 pipeline help path.

Artifact digest: `sha256:1f84752562ada908422d6ffd2346b9da9722503b4b44fc3fe9bb5a447d8dcb0d`

## Remaining scientific work

The environment is reproducibly identified, but this does not yet reproduce the scientific result. The next evidence step is to execute the April 11 low/high-band reconstruction, preserve the FITS bytes and logs, repeat it for determinism, and compare scientific image metrics.
