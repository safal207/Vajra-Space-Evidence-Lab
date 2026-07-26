# Ed25519 Attestation Signatures

## Purpose

Vajra reproduction attestations can be signed with Ed25519 so that any third party can verify integrity without access to private signing material.

A valid signature proves that:

1. the attestation bytes and signed authentication metadata have not changed;
2. the signer controlled the corresponding private key at signing time;
3. the public key matches the fingerprint and signer registry entry;
4. the registry policy accepts the signer for the declared signing time.

A valid signature does **not** prove that:

- the scientific claim is true;
- the runtime was honestly configured;
- the source data were complete;
- the signer was independent;
- the repository registry itself is trustworthy;
- the declared timestamp came from an external trusted timestamp authority.

Those properties require separate evidence.

## Signed payload

The Ed25519 payload contains both:

- the complete attestation with any previous `authentication` object removed;
- authentication metadata excluding the signature itself.

Authentication metadata includes:

- `algorithm`;
- `key_id`;
- public-key fingerprint;
- `signed_at`;
- optional `expires_at`;
- signer-registry version.

This prevents an attacker from changing the signer identity, fingerprint, time, expiry, or registry version without invalidating the signature.

## Signer registry

Published signer keys are stored in:

- `trust/signer-registry.json`
- `trust/keys/`

The registry supports:

- `active` — may sign new attestations inside its validity window;
- `retired` — historical signatures remain valid, but signatures after `retired_at` are rejected;
- `revoked` — acceptance depends on `revocation_mode`.

Revocation modes:

- `prospective` — signatures before `revoked_at` remain valid;
- `retroactive` — all signatures from that key are rejected.

Verification distinguishes:

- valid signature;
- malformed signature metadata;
- unknown signer;
- fingerprint mismatch;
- invalid signature;
- signature before key validity;
- signature after key retirement or validity expiration;
- expired attestation;
- revoked signer.

## Commands

Generate a keypair:

```bash
python scripts/ed25519_attestation.py generate \
  --private-key private/attestation-key.pem \
  --public-key trust/keys/attestation-key.pub.pem \
  --passphrase-env VAJRA_KEY_PASSPHRASE
```

Sign an attestation:

```bash
python scripts/ed25519_attestation.py sign attestation.json \
  --private-key private/attestation-key.pem \
  --passphrase-env VAJRA_KEY_PASSPHRASE \
  --key-id vajra-release-2026-01 \
  --output attestation.signed.json
```

Verify with only public information:

```bash
python scripts/ed25519_attestation.py verify \
  cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json \
  --registry trust/signer-registry.json
```

A successful verification exits with code `0` and emits `status: valid`.

## First published signature

The M87 Podman attestation is signed by:

- key ID: `vajra-m87-podman-ceremony-2026-07-26`
- fingerprint: `sha256:7b2b0152eb08c728e7d11e519703aeb300cdb9cc1f83fdeef5f5bb00ffff28a1`
- status: `retired`

The key was generated for a one-time signing ceremony. Its private material was not retained or committed. Retirement means the published historical signature remains verifiable while the key cannot authorize future attestations under registry policy.

## Threat model and limitations

### Repository compromise

An attacker controlling the repository could replace both the signed attestation and signer registry. Consumers requiring stronger trust should pin a registry commit or hash through an independent channel.

### Private-key compromise

A compromised active private key can sign false attestations. Rotate the key immediately and choose prospective or retroactive revocation based on incident scope.

### Timestamp trust

`signed_at` is signed but self-declared. It is not a trusted timestamp. Future versions may bind signatures to transparency logs or external timestamp authorities.

### Scientific independence

Multiple valid signatures from the same organization or infrastructure do not establish independent scientific confirmation. Signer identity, infrastructure independence, data independence, and method independence must be modeled separately.

### Key destruction claims

The registry can record that private material was destroyed, but software verification cannot prove destruction. This is an operational claim and should be supported by ceremony records when higher assurance is needed.
