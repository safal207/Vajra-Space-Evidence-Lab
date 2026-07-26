from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from vajra_space.signatures import (
    public_key_fingerprint,
    serialize_public_key,
    sign_attestation_ed25519,
    verify_attestation_ed25519,
)


UTC = timezone.utc
SIGNED_AT = datetime(2026, 7, 26, 20, 14, 10, tzinfo=UTC)


def attestation() -> dict:
    return {
        "attestation_version": 1,
        "manifest_id": "reproduction:test",
        "manifest_version": 1,
        "manifest_sha256": "a" * 64,
        "status": "success",
        "observed_outputs": [{"path": "output.bin", "sha256": "b" * 64}],
    }


def entry(
    private_key: Ed25519PrivateKey,
    *,
    key_id: str = "test-key",
    status: str = "active",
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    retired_at: datetime | None = None,
    revoked_at: datetime | None = None,
    revocation_mode: str | None = None,
) -> dict:
    public_key = private_key.public_key()
    return {
        "key_id": key_id,
        "algorithm": "ed25519",
        "public_key_pem": serialize_public_key(public_key).decode("utf-8"),
        "fingerprint": public_key_fingerprint(public_key),
        "status": status,
        "valid_from": (valid_from or datetime(2026, 1, 1, tzinfo=UTC)).isoformat(),
        "valid_until": None if valid_until is None else valid_until.isoformat(),
        "retired_at": None if retired_at is None else retired_at.isoformat(),
        "revoked_at": None if revoked_at is None else revoked_at.isoformat(),
        "revocation_mode": revocation_mode,
        "superseded_by": None,
        "trust_scope": "test fixture",
        "notes": "Generated in memory for unit testing.",
    }


def registry(*entries: dict) -> dict:
    return {
        "registry_version": 1,
        "updated_at": "2026-07-26T20:14:10Z",
        "trust_scope": "unit tests",
        "keys": list(entries),
    }


def test_valid_ed25519_signature_is_publicly_verifiable() -> None:
    private_key = Ed25519PrivateKey.generate()
    signed = sign_attestation_ed25519(
        attestation(),
        private_key,
        key_id="test-key",
        signed_at=SIGNED_AT,
    )

    result = verify_attestation_ed25519(
        signed,
        registry(entry(private_key)),
        now=SIGNED_AT + timedelta(minutes=1),
    )

    assert result.valid
    assert result.status == "valid"
    assert result.key_id == "test-key"


def test_tampering_invalidates_signature() -> None:
    private_key = Ed25519PrivateKey.generate()
    signed = sign_attestation_ed25519(attestation(), private_key, key_id="test-key", signed_at=SIGNED_AT)
    signed["status"] = "mismatch"

    result = verify_attestation_ed25519(signed, registry(entry(private_key)), now=SIGNED_AT)

    assert not result.valid
    assert result.status == "invalid_signature"


def test_wrong_public_key_is_distinguished_from_bad_signature() -> None:
    signing_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()
    signed = sign_attestation_ed25519(attestation(), signing_key, key_id="test-key", signed_at=SIGNED_AT)

    result = verify_attestation_ed25519(signed, registry(entry(wrong_key)), now=SIGNED_AT)

    assert not result.valid
    assert result.status == "fingerprint_mismatch"


def test_unknown_signer_is_reported() -> None:
    private_key = Ed25519PrivateKey.generate()
    signed = sign_attestation_ed25519(attestation(), private_key, key_id="missing", signed_at=SIGNED_AT)

    result = verify_attestation_ed25519(signed, registry(), now=SIGNED_AT)

    assert not result.valid
    assert result.status == "unknown_signer"


def test_retired_key_remains_valid_for_historical_signature() -> None:
    private_key = Ed25519PrivateKey.generate()
    retired_at = SIGNED_AT + timedelta(hours=1)
    signed = sign_attestation_ed25519(attestation(), private_key, key_id="retired", signed_at=SIGNED_AT)

    result = verify_attestation_ed25519(
        signed,
        registry(entry(private_key, key_id="retired", status="retired", retired_at=retired_at)),
        now=retired_at + timedelta(days=1),
    )

    assert result.valid
    assert result.status == "valid"


def test_signature_after_key_retirement_is_expired_signer() -> None:
    private_key = Ed25519PrivateKey.generate()
    retired_at = SIGNED_AT - timedelta(seconds=1)
    signed = sign_attestation_ed25519(attestation(), private_key, key_id="retired", signed_at=SIGNED_AT)

    result = verify_attestation_ed25519(
        signed,
        registry(entry(private_key, key_id="retired", status="retired", retired_at=retired_at)),
        now=SIGNED_AT,
    )

    assert not result.valid
    assert result.status == "expired_signer"


def test_retroactively_revoked_key_invalidates_historical_signature() -> None:
    private_key = Ed25519PrivateKey.generate()
    signed = sign_attestation_ed25519(attestation(), private_key, key_id="revoked", signed_at=SIGNED_AT)

    result = verify_attestation_ed25519(
        signed,
        registry(entry(
            private_key,
            key_id="revoked",
            status="revoked",
            revoked_at=SIGNED_AT + timedelta(hours=1),
            revocation_mode="retroactive",
        )),
        now=SIGNED_AT + timedelta(days=1),
    )

    assert not result.valid
    assert result.status == "revoked_signer"


def test_prospective_revocation_preserves_earlier_signature() -> None:
    private_key = Ed25519PrivateKey.generate()
    revoked_at = SIGNED_AT + timedelta(hours=1)
    signed = sign_attestation_ed25519(attestation(), private_key, key_id="revoked", signed_at=SIGNED_AT)

    result = verify_attestation_ed25519(
        signed,
        registry(entry(
            private_key,
            key_id="revoked",
            status="revoked",
            revoked_at=revoked_at,
            revocation_mode="prospective",
        )),
        now=revoked_at + timedelta(days=1),
    )

    assert result.valid
    assert result.status == "valid"


def test_expired_attestation_is_distinguished_from_expired_key() -> None:
    private_key = Ed25519PrivateKey.generate()
    signed = sign_attestation_ed25519(
        attestation(),
        private_key,
        key_id="test-key",
        signed_at=SIGNED_AT,
        expires_at=SIGNED_AT + timedelta(minutes=5),
    )

    result = verify_attestation_ed25519(
        signed,
        registry(entry(private_key)),
        now=SIGNED_AT + timedelta(minutes=6),
    )

    assert not result.valid
    assert result.status == "expired_attestation"
