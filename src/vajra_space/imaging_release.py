from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "README.md",
    "run.sh",
    "eht-imaging/README.md",
    "eht-imaging/eht-imaging_pipeline.py",
    "eht-imaging/run.sh",
    "difmap/README.md",
    "smili/README.md",
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


def build_imaging_release_manifest(repo: Path) -> dict[str, Any]:
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
        raise ValueError(f"Imaging release is missing required files: {missing}")

    objects: list[dict[str, Any]] = []
    tree_hasher = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(repo).as_posix()
        digest = sha256_file(path)
        size = path.stat().st_size
        if digest == "0" * 64:
            raise ValueError(f"Invalid all-zero digest for {relative}")
        objects.append({
            "path": relative,
            "size_bytes": size,
            "sha256": digest,
        })
        tree_hasher.update(f"{digest} {size} {relative}\n".encode("utf-8"))

    return {
        "manifest_version": 1,
        "source_repository": remote,
        "source_commit": commit,
        "data_product_code": "2019-D01-02",
        "primary_reference_doi": "10.3847/2041-8213/ab0e85",
        "selected_pipeline": "eht-imaging",
        "declared_eht_imaging_version": "1.1.0",
        "object_count": len(objects),
        "release_tree_sha256": tree_hasher.hexdigest(),
        "objects": objects,
    }


def write_imaging_release_manifest(repo: Path, output: Path) -> dict[str, Any]:
    manifest = build_imaging_release_manifest(repo)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
