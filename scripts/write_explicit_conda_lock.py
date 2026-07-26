from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _package_url(record: dict[str, Any]) -> str:
    direct = record.get("url")
    if isinstance(direct, str) and direct.startswith(("https://", "http://")):
        return direct

    filename = record.get("fn") or record.get("filename")
    if not isinstance(filename, str) or not filename:
        raise ValueError(f"missing package filename for {record.get('name')}")

    channel = record.get("channel") or record.get("base_url")
    subdir = record.get("subdir") or record.get("platform")
    if not isinstance(channel, str) or not channel.startswith(("https://", "http://")):
        raise ValueError(f"missing immutable channel URL for {record.get('name')}")

    channel = channel.rstrip("/")
    if isinstance(subdir, str) and subdir and not channel.endswith(f"/{subdir}"):
        channel = f"{channel}/{subdir}"
    return f"{channel}/{filename}"


def build_explicit_lock(prefix: Path) -> str:
    metadata_dir = prefix / "conda-meta"
    records: list[tuple[str, str]] = []

    for path in sorted(metadata_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        url = _package_url(record)
        checksum = record.get("md5")
        if not isinstance(checksum, str) or len(checksum) != 32:
            raise ValueError(f"missing MD5 for {record.get('name')}")
        records.append((url, checksum))

    if not records:
        raise ValueError(f"no Conda package records found in {metadata_dir}")

    lines = [
        "# Generated from installed conda-meta records.",
        "# platform: linux-64",
        "@EXPLICIT",
    ]
    lines.extend(f"{url}#{checksum}" for url, checksum in sorted(records))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    content = build_explicit_lock(args.prefix)
    args.output.write_text(content, encoding="utf-8")
    print(f"wrote {content.count(chr(10)) - 3} exact package records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
