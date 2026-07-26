from __future__ import annotations

import argparse
import json
from pathlib import Path

from vajra_space.imaging_release import write_imaging_release_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = write_imaging_release_manifest(args.repository, args.output)
    print(json.dumps({
        "source_commit": manifest["source_commit"],
        "object_count": manifest["object_count"],
        "release_tree_sha256": manifest["release_tree_sha256"],
        "selected_pipeline": manifest["selected_pipeline"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
