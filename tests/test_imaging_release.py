from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vajra_space.imaging_release import REQUIRED_FILES, build_imaging_release_manifest


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def make_release(repo: Path) -> None:
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Vajra Test")
    git(repo, "config", "user.email", "vajra@example.invalid")
    git(repo, "remote", "add", "origin", "https://github.com/eventhorizontelescope/2019-D01-02.git")
    for index, name in enumerate(sorted(REQUIRED_FILES), start=1):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fixture-{index}-{name}\n".encode("utf-8"))
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture imaging release")


def test_imaging_manifest_is_deterministic_and_complete(tmp_path: Path) -> None:
    repo = tmp_path / "imaging-release"
    make_release(repo)

    first = build_imaging_release_manifest(repo)
    second = build_imaging_release_manifest(repo)

    assert first == second
    assert first["data_product_code"] == "2019-D01-02"
    assert first["selected_pipeline"] == "eht-imaging"
    assert first["declared_eht_imaging_version"] == "1.1.0"
    assert first["object_count"] == len(REQUIRED_FILES)
    assert len(first["release_tree_sha256"]) == 64
    assert {item["path"] for item in first["objects"]} == REQUIRED_FILES
    assert all(item["size_bytes"] > 0 for item in first["objects"])
    assert all(item["sha256"] != "0" * 64 for item in first["objects"])


def test_imaging_manifest_rejects_missing_pipeline_file(tmp_path: Path) -> None:
    repo = tmp_path / "imaging-release"
    make_release(repo)
    (repo / "eht-imaging/eht-imaging_pipeline.py").unlink()

    with pytest.raises(ValueError, match="missing required files"):
        build_imaging_release_manifest(repo)
