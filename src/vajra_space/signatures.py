from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .reproduction import canonical_json


VERIFICATION_STATUSES = (
    "valid",
    "malformed",
    "unknown_signer",
    "fingerprint_mismatch",
    "invalid_signature",
    "not_yet_valid",
    "expired_signer",
    "expired_attestation",
    "revoked_signer",
)


@dataclass(frozen=True)
class SignatureVerification:
    valid: bool
    status: str
    key_id: str | None
    fingerprint: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "status": self.status,
            "key_id": self.key_id,
            "fingerprint": self.fingerprint,
            "message": self.message,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def public_key_fingerprint(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def serialize_private_key(private_key: Ed25519PrivateKey, passphrase: bytes | None = None) -> bytes:
    encryption = (
        serialization.NoEncryption()
        if passphrase is None
        else serialization.BestAvailableEncryption(passphrase)
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )


def serialize_public_key(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_private_key(pem: bytes, passphrase: bytes | None = None) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(pem, password=passphrase)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Private key is not Ed25519")
    return key


def load_public_key(pem: bytes) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("Public key is not Ed25519")
    return key


def generate_keypair(passphrase: bytes | None = None) -> tuple[bytes, bytes, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return (
        serialize_private_key(private_key, passphrase),
        serialize_public_key(public_key),
        public_key_fingerprint(public_key),
    )


def _unsigned_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(attestation)
    unsigned.pop("authentication", None)
    return unsigned


def _signature_payload(unsigned: dict[str, Any], metadata: dict[str, Any]) -> bytes:
    return canonical_json({"attestation": unsigned, "authentication": metadata}).encode("utf-8")


def sign_attestation_ed25519(
    attestation: dict[str, Any],
    private_key: Ed25519PrivateKey,
    *,
    key_id: str,
    signed_at: datetime | None = None,
    expires_at: datetime | None = None,
    registry_version: int = 1,
) -> dict[str, Any]:
    if not key_id:
        raise ValueError("key_id is required")
    signed_at = signed_at or _utc_now()
    public_key = private_key.public_key()
    metadata: dict[str, Any] = {
        "algorithm": "ed25519",
        "key_id": key_id,
        "public_key_fingerprint": public_key_fingerprint(public_key),
        "signed_at": _format_time(signed_at),
        "expires_at": None if expires_at is None else _format_time(expires_at),
        "registry_version": registry_version,
    }
    unsigned = _unsigned_attestation(attestation)
    signature = private_key.sign(_signature_payload(unsigned, metadata))
    signed = dict(unsigned)
    signed["authentication"] = {
        **metadata,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    return signed


def _result(
    valid: bool,
    status: str,
    key_id: str | None,
    fingerprint: str | None,
    message: str,
) -> SignatureVerification:
    if status not in VERIFICATION_STATUSES:
        raise ValueError(f"Unknown signature verification status: {status}")
    return SignatureVerification(valid, status, key_id, fingerprint, message)


def verify_attestation_ed25519(
    attestation: dict[str, Any],
    registry: dict[str, Any],
    *,
    now: datetime | None = None,
) -> SignatureVerification:
    now = now or _utc_now()
    authentication = attestation.get("authentication")
    if not isinstance(authentication, dict):
        return _result(False, "malformed", None, None, "Missing authentication object")
    if authentication.get("algorithm") != "ed25519":
        return _result(False, "malformed", authentication.get("key_id"), None, "Unsupported signature algorithm")

    key_id = authentication.get("key_id")
    fingerprint = authentication.get("public_key_fingerprint")
    supplied_signature = authentication.get("signature")
    if not all(isinstance(value, str) and value for value in (key_id, fingerprint, supplied_signature)):
        return _result(False, "malformed", key_id if isinstance(key_id, str) else None, fingerprint if isinstance(fingerprint, str) else None, "Incomplete signature metadata")

    key_entries = registry.get("keys")
    if not isinstance(key_entries, list):
        return _result(False, "malformed", key_id, fingerprint, "Signer registry has no keys array")
    entry = next((item for item in key_entries if item.get("key_id") == key_id), None)
    if entry is None:
        return _result(False, "unknown_signer", key_id, fingerprint, "Signer key is not present in the registry")

    try:
        public_key = load_public_key(entry["public_key_pem"].encode("utf-8"))
    except (KeyError, TypeError, ValueError) as exc:
        return _result(False, "malformed", key_id, fingerprint, f"Invalid registry public key: {exc}")

    calculated_fingerprint = public_key_fingerprint(public_key)
    registry_fingerprint = entry.get("fingerprint")
    if fingerprint != calculated_fingerprint or registry_fingerprint != calculated_fingerprint:
        return _result(False, "fingerprint_mismatch", key_id, calculated_fingerprint, "Public-key fingerprint does not match the signed or registered value")

    metadata = dict(authentication)
    metadata.pop("signature", None)
    unsigned = _unsigned_attestation(attestation)
    try:
        signature = base64.b64decode(supplied_signature, validate=True)
        public_key.verify(signature, _signature_payload(unsigned, metadata))
    except (InvalidSignature, ValueError):
        return _result(False, "invalid_signature", key_id, calculated_fingerprint, "Ed25519 signature verification failed")

    try:
        signed_at = _parse_time(authentication.get("signed_at"))
        expires_at = _parse_time(authentication.get("expires_at"))
        valid_from = _parse_time(entry.get("valid_from"))
        valid_until = _parse_time(entry.get("valid_until"))
        retired_at = _parse_time(entry.get("retired_at"))
        revoked_at = _parse_time(entry.get("revoked_at"))
    except (TypeError, ValueError) as exc:
        return _result(False, "malformed", key_id, calculated_fingerprint, f"Invalid timestamp metadata: {exc}")

    if signed_at is None:
        return _result(False, "malformed", key_id, calculated_fingerprint, "signed_at is required")
    if valid_from is not None and signed_at < valid_from:
        return _result(False, "not_yet_valid", key_id, calculated_fingerprint, "Attestation predates the signer's validity window")
    if valid_until is not None and signed_at > valid_until:
        return _result(False, "expired_signer", key_id, calculated_fingerprint, "Attestation was signed after the signer's validity window")
    if retired_at is not None and signed_at > retired_at:
        return _result(False, "expired_signer", key_id, calculated_fingerprint, "Attestation was signed after the key was retired")
    if expires_at is not None and now > expires_at:
        return _result(False, "expired_attestation", key_id, calculated_fingerprint, "Attestation signature has expired")

    status = entry.get("status", "unknown")
    if status == "revoked":
        revocation_mode = entry.get("revocation_mode", "retroactive")
        if revocation_mode == "retroactive" or revoked_at is None or signed_at >= revoked_at:
            return _result(False, "revoked_signer", key_id, calculated_fingerprint, "Signer key is revoked")
    elif status not in {"active", "retired"}:
        return _result(False, "unknown_signer", key_id, calculated_fingerprint, f"Signer status is not trusted: {status}")

    return _result(True, "valid", key_id, calculated_fingerprint, "Ed25519 signature and signer policy are valid")
