from __future__ import annotations

import argparse
import json
from pathlib import Path

from vajra_space.image_comparison import compare_feature_files


EXIT_CODES = {
    "pass": 0,
    "incomplete": 2,
    "mismatch": 3,
    "invalid_contract": 4,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("features", type=Path)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("cases/m87-black-hole/m87-image-comparison-contract.json"),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/image-comparison.schema.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = compare_feature_files(args.features, args.contract, args.schema)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return EXIT_CODES[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
