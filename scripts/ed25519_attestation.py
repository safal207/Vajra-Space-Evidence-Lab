from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from vajra_space.signatures import (
    generate_keypair,
    load_private_key,
    sign_attestation_ed25519,
    verify_attestation_ed25519,
)


def parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def command_generate(args: argparse.Namespace) -> int:
    passphrase = None
    if args.passphrase_env:
        value = os.environ.get(args.passphrase_env)
        if value is None:
            raise SystemExit(f"Missing environment variable: {args.passphrase_env}")
        passphrase = value.encode("utf-8")

    private_pem, public_pem, fingerprint = generate_keypair(passphrase)
    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    args.public_key.parent.mkdir(parents=True, exist_ok=True)
    args.private_key.write_bytes(private_pem)
    os.chmod(args.private_key, 0o600)
    args.public_key.write_bytes(public_pem)
    print(json.dumps({
        "private_key": str(args.private_key),
        "public_key": str(args.public_key),
        "fingerprint": fingerprint,
    }, indent=2))
    return 0


def command_sign(args: argparse.Namespace) -> int:
    passphrase = None
    if args.passphrase_env:
        value = os.environ.get(args.passphrase_env)
        if value is None:
            raise SystemExit(f"Missing environment variable: {args.passphrase_env}")
        passphrase = value.encode("utf-8")

    attestation = json.loads(args.attestation.read_text(encoding="utf-8"))
    private_key = load_private_key(args.private_key.read_bytes(), passphrase)
    signed = sign_attestation_ed25519(
        attestation,
        private_key,
        key_id=args.key_id,
        signed_at=parse_time(args.signed_at),
        expires_at=parse_time(args.expires_at),
        registry_version=args.registry_version,
    )
    encoded = json.dumps(signed, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    attestation = json.loads(args.attestation.read_text(encoding="utf-8"))
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = verify_attestation_ed25519(
        attestation,
        registry,
        now=parse_time(args.now),
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.valid else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate")
    generate.add_argument("--private-key", type=Path, required=True)
    generate.add_argument("--public-key", type=Path, required=True)
    generate.add_argument("--passphrase-env")
    generate.set_defaults(handler=command_generate)

    sign = sub.add_parser("sign")
    sign.add_argument("attestation", type=Path)
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--key-id", required=True)
    sign.add_argument("--output", type=Path, required=True)
    sign.add_argument("--signed-at")
    sign.add_argument("--expires-at")
    sign.add_argument("--registry-version", type=int, default=1)
    sign.add_argument("--passphrase-env")
    sign.set_defaults(handler=command_sign)

    verify = sub.add_parser("verify")
    verify.add_argument("attestation", type=Path)
    verify.add_argument("--registry", type=Path, required=True)
    verify.add_argument("--now")
    verify.set_defaults(handler=command_verify)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
