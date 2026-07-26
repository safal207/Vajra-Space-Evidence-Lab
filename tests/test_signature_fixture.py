from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from vajra_space.signatures import (
    load_public_key,
    public_key_fingerprint,
    verify_attestation_ed25519,
)


ROOT = Path(__file__).resolve().parents[1]
SIGNED = ROOT / "cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json"
RESULT = ROOT / "cases/m87-black-hole/m87-ehtim-podman-confirmation.json"
REGISTRY = ROOT / "trust/signer-registry.json"
PUBLIC_KEY = ROOT / "trust/keys/vajra-m87-podman-ceremony-2026-07-26.pub.pem"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_published_signer_registry_is_schema_valid() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/signer-registry.schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry))
    assert errors == []


def test_published_public_key_matches_registry_fingerprint() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    public_key = load_public_key(PUBLIC_KEY.read_bytes())
    entry = registry["keys"][0]

    assert entry["key_id"] == "vajra-m87-podman-ceremony-2026-07-26"
    assert entry["status"] == "retired"
    assert entry["fingerprint"] == public_key_fingerprint(public_key)
    assert entry["public_key_pem"] == PUBLIC_KEY.read_text(encoding="utf-8")


def test_published_m87_attestation_verifies_after_key_retirement() -> None:
    signed = json.loads(SIGNED.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    result = verify_attestation_ed25519(
        signed,
        registry,
        now=datetime(2026, 7, 27, tzinfo=timezone.utc),
    )

    assert result.valid
    assert result.status == "valid"
    assert result.key_id == "vajra-m87-podman-ceremony-2026-07-26"
    assert result.fingerprint == "sha256:7b2b0152eb08c728e7d11e519703aeb300cdb9cc1f83fdeef5f5bb00ffff28a1"


def test_persisted_result_binds_exact_registry_and_signed_attestation_bytes() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    signature = result["signature"]

    assert signature["registry_path"] == "trust/signer-registry.json"
    assert signature["registry_sha256"] == sha256_file(REGISTRY)
    assert signature["registry_sha256"] == "06e305777985b97d09083dfa8c0579f285b59a503e9dcbdbbd239bc31e2fbba7"

    assert signature["signed_attestation_path"] == (
        "cases/m87-black-hole/m87-ehtim-podman-attestation.signed.json"
    )
    assert signature["signed_attestation_sha256"] == sha256_file(SIGNED)
    assert signature["signed_attestation_sha256"] == (
        "b13106e43dabab4c0051cf7dc1780aed46e8656aa7b18ad3d03332ce98516061"
    )


def test_published_signature_detects_result_tampering() -> None:
    signed = json.loads(SIGNED.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(signed)
    tampered["observed_outputs"][0]["sha256"] = "0" * 64

    result = verify_attestation_ed25519(
        tampered,
        registry,
        now=datetime(2026, 7, 27, tzinfo=timezone.utc),
    )

    assert not result.valid
    assert result.status == "invalid_signature"
