import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _package_url(record):
    # type: (Dict[str, Any]) -> str
    direct = record.get("url")
    if isinstance(direct, str) and direct.startswith(("https://", "http://")):
        return direct

    filename = record.get("fn") or record.get("filename")
    if not isinstance(filename, str) or not filename:
        raise ValueError("missing package filename for {}".format(record.get("name")))

    channel = record.get("channel") or record.get("base_url")
    subdir = record.get("subdir") or record.get("platform")
    if not isinstance(channel, str) or not channel.startswith(("https://", "http://")):
        raise ValueError("missing immutable channel URL for {}".format(record.get("name")))

    channel = channel.rstrip("/")
    if isinstance(subdir, str) and subdir and not channel.endswith("/{}".format(subdir)):
        channel = "{}/{}".format(channel, subdir)
    return "{}/{}".format(channel, filename)


def build_explicit_lock(prefix):
    # type: (Path) -> str
    metadata_dir = prefix / "conda-meta"
    records = []  # type: List[Tuple[str, str]]

    for path in sorted(metadata_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        url = _package_url(record)
        checksum = record.get("md5")
        if not isinstance(checksum, str) or len(checksum) != 32:
            raise ValueError("missing MD5 for {}".format(record.get("name")))
        records.append((url, checksum))

    if not records:
        raise ValueError("no Conda package records found in {}".format(metadata_dir))

    lines = [
        "# Generated from installed conda-meta records.",
        "# platform: linux-64",
        "@EXPLICIT",
    ]
    lines.extend("{}#{}".format(url, checksum) for url, checksum in sorted(records))
    return "\n".join(lines) + "\n"


def main():
    # type: () -> int
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    content = build_explicit_lock(args.prefix)
    args.output.write_text(content, encoding="utf-8")
    print("wrote {} exact package records".format(content.count("\n") - 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
