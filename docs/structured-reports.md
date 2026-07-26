# Structured CLI Reports

## Goal

Validator and reproduction commands can emit stable, versioned JSON suitable for CI, dashboards, evidence bundles, and downstream automation without parsing human-readable console text.

Human-readable behavior remains the default for backward compatibility. Add `--json` to request the common envelope.

## Common envelope

```json
{
  "report_version": 1,
  "tool": {
    "name": "vajra-space",
    "version": "0.4.0",
    "command": "validate-claim"
  },
  "input": {
    "path": "claim.json",
    "resolved_path": "/absolute/path/claim.json",
    "sha256": "..."
  },
  "status": "valid",
  "valid": true,
  "issues": []
}
```

Fields:

- `report_version` — version of the envelope contract;
- `tool.name` — stable CLI identity;
- `tool.version` — installed package version;
- `tool.command` — command that produced the report;
- `input.path` — path supplied by the operator;
- `input.resolved_path` — resolved filesystem path used during execution;
- `input.sha256` — digest of the exact input bytes;
- `status` — command-specific status;
- `valid` — `true` for `valid` or `success`, otherwise `false`;
- `issues` — deterministically sorted issue objects;
- `data` — optional command-specific payload.

## Issue contract

Every issue has exactly these common fields:

```json
{
  "code": "input_hash_mismatch",
  "path": "$.inputs.0.sha256",
  "message": "Input SHA-256 mismatch for input.dat"
}
```

Issues are sorted by:

1. `path`;
2. `code`;
3. `message`.

This makes report encoding stable even when an underlying validator discovers issues in a different order.

## Determinism

The common envelope intentionally does not add a generated timestamp. Given:

- the same installed tool version;
- the same command;
- the same input path and bytes;
- the same validator result;

the encoded JSON is deterministic.

Runtime attestations may contain timing fields because they describe an execution event. When `reproduce --json` is used, the attestation is placed under `data.attestation` while the outer envelope remains versioned and structurally stable.

## Supported commands

```bash
vajra-space validate-claim claim.json --json
vajra-space validate-evidence evidence.json --json
vajra-space validate-bundle evidence-bundle.json --json
vajra-space validate-reproduction-manifest manifest.json --json
vajra-space reproduce manifest.json --workspace workspace --execute --json
vajra-space verify-reproduction-attestation attestation.json \
  --signing-key-env VAJRA_HMAC_KEY --json
vajra-space ledger-validate ledger.json --json
```

## Backward compatibility

Without `--json`, existing output remains unchanged:

- successful validators print `VALID`;
- failed validators print one human-readable issue per line;
- `reproduce` prints the direct attestation JSON as before;
- HMAC verification prints `VALID` or `INVALID`.

The test suite checks both old and new modes.

## Reproduction statuses

The outer report preserves reproduction status:

- `success` — expected exit code and all declared output hashes match;
- `partial` — execution completed but one or more optional or undeclared comparisons remain;
- `mismatch` — execution or required output differs from the manifest;
- `blocked` — prerequisites, authorization, runtime, input integrity, or schema checks prevent execution.

Exit codes remain:

- `0` — success;
- `2` — partial;
- `3` — mismatch;
- `4` — blocked.

## Trust boundary

Structured output improves interoperability; it does not add trust by itself. Consumers should still verify:

- input digests;
- evidence-bundle hash links;
- reproduction output hashes;
- public signatures where present;
- the Git commit or release containing the report contract.
