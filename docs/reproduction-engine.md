# Reproduction Engine v0.1

The reproduction engine turns a pinned manifest into a deterministic attestation with one of four statuses:

- `success` — expected exit code and all declared output hashes match;
- `partial` — execution completed, but an optional output is missing or an expected output hash was not declared;
- `mismatch` — execution ran but the exit code, timeout, required output, or output hash violated the contract;
- `blocked` — prerequisites, authorization, input integrity, runtime availability, or path safety prevented execution.

## Safety defaults

Execution is denied unless the operator passes `--execute`.

Before execution the engine:

1. validates the manifest against `schemas/reproduction.schema.json`;
2. rejects absolute paths and paths escaping the workspace;
3. verifies every declared input SHA-256;
4. blocks when a declared output already exists;
5. requires container images to be pinned by `sha256` digest.

Container commands are constructed with:

- no network;
- read-only root filesystem;
- all Linux capabilities dropped;
- `no-new-privileges`;
- an unprivileged user by default;
- only the declared workspace mounted writable.

Runtime conformance testing is tracked separately because command construction alone does not prove that every OCI runtime enforces the flags identically.

## Validate a manifest

```bash
vajra-space validate-reproduction-manifest \
  examples/reproduction/local-smoke.json
```

## Plan without execution

The default is fail-closed and returns `blocked`:

```bash
vajra-space reproduce \
  examples/reproduction/local-smoke.json \
  --workspace .
```

## Execute

Run from a clean workspace where declared output files do not already exist:

```bash
vajra-space reproduce \
  examples/reproduction/local-smoke.json \
  --workspace . \
  --execute \
  --attestation reproduction-attestation.json
```

Exit codes:

| Code | Status |
|---:|---|
| 0 | success |
| 2 | partial |
| 3 | mismatch |
| 4 | blocked |

## Authenticate an attestation

v0.1 supports optional HMAC-SHA256 authentication. The secret is read from an environment variable and is never written into the attestation.

```bash
export VAJRA_ATTESTATION_KEY='replace-with-secret-material'

vajra-space reproduce \
  examples/reproduction/local-smoke.json \
  --workspace . \
  --execute \
  --attestation reproduction-attestation.json \
  --signing-key-env VAJRA_ATTESTATION_KEY \
  --key-id local-test-key

vajra-space verify-reproduction-attestation \
  reproduction-attestation.json \
  --signing-key-env VAJRA_ATTESTATION_KEY
```

HMAC authentication is useful for controlled pipelines but is not publicly verifiable. Ed25519 support, key rotation, and revocation are tracked as follow-up work.

## Attestation contents

The report records:

- manifest identity and SHA-256;
- start, finish, and duration;
- runtime snapshot;
- expected and observed exit codes;
- stdout and stderr hashes;
- observed output sizes and hashes;
- structured issues;
- final status;
- attestation digest;
- optional authentication metadata.

The engine does not claim scientific reproduction merely because a command returned successfully. Scientific meaning still depends on the manifest binding the correct data, code, parameters, environment, comparison metrics, and uncertainty contract.
