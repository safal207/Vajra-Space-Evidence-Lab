from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "m87-black-hole"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict[str, Any]:
    plan = json.loads((CASE / "eht-imaging-reproduction-plan.json").read_text(encoding="utf-8"))
    provenance = json.loads((CASE / "m87-ehtim-environment-provenance.json").read_text(encoding="utf-8"))
    environment = plan["environment"]

    lock_path = ROOT / environment["lock_path"]
    patch_path = ROOT / environment["compatibility_patch"]["path"]
    actual_lock_hash = sha256_file(lock_path)
    actual_patch_hash = sha256_file(patch_path)

    checks = {
        "oci_reference": environment["oci_reference"] == provenance["oci_reference"],
        "base_reference": environment["base_reference"] == provenance["base_reference"],
        "platform": environment["platform"] == provenance["platform"],
        "declared_lock_hash": environment["lock_sha256"] == provenance["environment_lock_sha256"],
        "actual_lock_hash": actual_lock_hash == provenance["environment_lock_sha256"],
        "upstream_commit": environment["upstream_ehtim"]["commit"] == provenance["ehtim_commit"],
        "upstream_tree": environment["upstream_ehtim"]["tree_sha256"] == provenance["ehtim_tree_sha256"],
        "declared_patch_hash": environment["compatibility_patch"]["sha256"] == provenance["compatibility_patch_sha256"],
        "actual_patch_hash": actual_patch_hash == provenance["compatibility_patch_sha256"],
        "workflow_run": environment["verification"]["workflow_run_id"] == provenance["workflow_run_id"],
        "artifact_digest": environment["verification"]["artifact_digest"] == provenance["artifact_digest"],
    }

    return {
        "report_version": 1,
        "valid": all(checks.values()),
        "checks": checks,
        "actual": {
            "lock_sha256": actual_lock_hash,
            "patch_sha256": actual_patch_hash,
        },
        "declared": {
            "lock_sha256": provenance["environment_lock_sha256"],
            "patch_sha256": provenance["compatibility_patch_sha256"],
            "oci_reference": provenance["oci_reference"],
            "workflow_run_id": provenance["workflow_run_id"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
