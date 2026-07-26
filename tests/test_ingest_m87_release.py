from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vajra_space.release_ingest import REQUIRED_FILES, build_manifest


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def make_release(repo: Path) -> None:
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Vajra Test")
    git(repo, "config", "user.email", "vajra@example.invalid")
    git(repo, "remote", "add", "origin", "https://github.com/eventhorizontelescope/2019-D01-01.git")
    for index, name in enumerate(sorted(REQUIRED_FILES), start=1):
        path = repo / name
        path.write_bytes(f"fixture-{index}-{name}\n".encode("utf-8"))
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture release")


def test_manifest_is_deterministic_and_complete(tmp_path: Path) -> None:
    repo = tmp_path / "release"
    make_release(repo)

    first = build_manifest(repo)
    second = build_manifest(repo)

    assert first == second
    assert first["doi"] == "10.25739/g85n-f134"
    assert first["data_product_code"] == "2019-D01-01"
    assert first["object_count"] == len(REQUIRED_FILES)
    assert len(first["release_tree_sha256"]) == 64
    assert {item["path"] for item in first["objects"]} == REQUIRED_FILES
    assert all(item["size_bytes"] > 0 for item in first["objects"])
    assert all(item["sha256"] != "0" * 64 for item in first["objects"])


def test_manifest_rejects_missing_required_file(tmp_path: Path) -> None:
    repo = tmp_path / "release"
    make_release(repo)
    (repo / "INVENTORY.txt").unlink()

    with pytest.raises(ValueError, match="missing required files"):
        build_manifest(repo)
