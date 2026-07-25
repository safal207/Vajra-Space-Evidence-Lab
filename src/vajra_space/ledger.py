from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LedgerValidation:
    valid: bool
    errors: tuple[str, ...]


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_record(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("record_hash", None)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def append_record(
    ledger_path: Path,
    claim: dict[str, Any],
    *,
    event_type: str,
    actor: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    if ledger_path.exists():
        records = json.loads(ledger_path.read_text(encoding="utf-8"))

    previous_hash = records[-1]["record_hash"] if records else None
    record = {
        "sequence": len(records) + 1,
        "event_type": event_type,
        "actor": actor,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claim_id": claim["claim_id"],
        "claim_version": claim["version"],
        "claim_status": claim["status"],
        "claim_snapshot_hash": hashlib.sha256(
            canonical_json(claim).encode("utf-8")
        ).hexdigest(),
        "previous_record_hash": previous_hash,
    }
    record["record_hash"] = hash_record(record)
    records.append(record)
    ledger_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return record


def validate_ledger_records(records: list[dict[str, Any]]) -> LedgerValidation:
    errors: list[str] = []
    previous_hash: str | None = None
    seen_versions: dict[str, int] = {}

    for index, record in enumerate(records, start=1):
        if record.get("sequence") != index:
            errors.append(f"record {index}: sequence must equal {index}")

        if record.get("previous_record_hash") != previous_hash:
            errors.append(f"record {index}: previous_record_hash mismatch")

        if record.get("record_hash") != hash_record(record):
            errors.append(f"record {index}: record_hash mismatch")

        claim_id = record.get("claim_id")
        version = record.get("claim_version")
        if not isinstance(claim_id, str) or not isinstance(version, int):
            errors.append(f"record {index}: invalid claim identity/version")
        else:
            last = seen_versions.get(claim_id, 0)
            if version < last:
                errors.append(f"record {index}: claim version regressed")
            seen_versions[claim_id] = max(last, version)

        previous_hash = record.get("record_hash")

    return LedgerValidation(valid=not errors, errors=tuple(errors))


def validate_ledger_file(path: Path) -> LedgerValidation:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        return LedgerValidation(False, ("ledger root must be an array",))
    return validate_ledger_records(records)
