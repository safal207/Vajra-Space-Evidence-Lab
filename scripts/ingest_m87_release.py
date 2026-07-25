from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "README.md",
    "INVENTORY.txt",
    "LICENSE.txt",
    "run.sh",
    "EHTC_FirstM87Results_Apr2019_uvfits.tgz",
    "EHTC_FirstM87Results_Apr2019_txt.tgz",
    "EHTC_FirstM87Results_Apr2019_csv.tgz",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def build_manifest(repo: Path) -> dict[str, Any]:
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise ValueError(f"Not a git repository: {repo}")

    commit = git_output(repo, "rev-parse", "HEAD")
    remote = git_output(repo, "config", "--get", "remote.origin.url")

    paths = sorted(
        path
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    )
    relative_paths = {path.relative_to(repo).as_posix() for path in paths}
    missing = sorted(REQUIRED_FILES - relative_paths)
    if missing:
        raise ValueError(f"Release is missing required files: {missing}")

    objects: list[dict[str, Any]] = []
    tree_hasher = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(repo).as_posix()
        digest = sha256_file(path)
        size = path.stat().st_size
        if digest == "0" * 64:
            raise ValueError(f"Invalid all-zero digest for {relative}")
        objects.append(
            {
                "path": relative,
                "size_bytes": size,
                "sha256": digest,
            }
        )
        tree_hasher.update(f"{digest} {size} {relative}\n".encode("utf-8"))

    return {
        "manifest_version": 1,
        "source_repository": remote,
        "source_commit": commit,
        "doi": "10.25739/g85n-f134",
        "data_product_code": "2019-D01-01",
        "object_count": len(objects),
        "release_tree_sha256": tree_hasher.hexdigest(),
        "objects": objects,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = build_manifest(args.repository)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_commit": manifest["source_commit"],
                "object_count": manifest["object_count"],
                "release_tree_sha256": manifest["release_tree_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
