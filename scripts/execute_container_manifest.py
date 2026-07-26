from __future__ import annotations

import argparse
import json
from pathlib import Path

from vajra_space.container_runtime import execute_container_manifest


EXIT_CODES = {
    "success": 0,
    "partial": 2,
    "mismatch": 3,
    "blocked": 4,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("schemas/reproduction.schema.json"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    attestation = execute_container_manifest(
        args.manifest,
        args.schema,
        args.workspace,
        allow_execution=args.execute,
    )
    encoded = json.dumps(attestation, indent=2, sort_keys=True) + "\n"
    args.attestation.parent.mkdir(parents=True, exist_ok=True)
    args.attestation.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return EXIT_CODES[attestation["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
