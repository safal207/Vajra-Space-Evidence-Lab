from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable


REPORT_VERSION = 1
TOOL_NAME = "vajra-space"
FALLBACK_TOOL_VERSION = "0.4.0"


def tool_version() -> str:
    try:
        return metadata.version("vajra-space-evidence-lab")
    except metadata.PackageNotFoundError:
        return FALLBACK_TOOL_VERSION


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _issue_dict(issue: Any) -> dict[str, str]:
    if isinstance(issue, dict):
        value = issue
    elif is_dataclass(issue):
        value = asdict(issue)
    elif isinstance(issue, str):
        value = {"code": "error", "path": "$", "message": issue}
    else:
        value = {
            "code": getattr(issue, "code", "error"),
            "path": getattr(issue, "path", "$"),
            "message": getattr(issue, "message", str(issue)),
        }
    return {
        "code": str(value.get("code", "error")),
        "path": str(value.get("path", "$")),
        "message": str(value.get("message", "")),
    }


def normalize_issues(issues: Iterable[Any]) -> list[dict[str, str]]:
    normalized = [_issue_dict(issue) for issue in issues]
    return sorted(
        normalized,
        key=lambda item: (item["path"], item["code"], item["message"]),
    )


def build_report(
    *,
    command: str,
    input_path: Path,
    status: str,
    issues: Iterable[Any] = (),
    data: Any = None,
) -> dict[str, Any]:
    resolved = input_path.resolve()
    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "tool": {
            "name": TOOL_NAME,
            "version": tool_version(),
            "command": command,
        },
        "input": {
            "path": str(input_path),
            "resolved_path": str(resolved),
            "sha256": sha256_file(resolved),
        },
        "status": status,
        "valid": status in {"valid", "success"},
        "issues": normalize_issues(issues),
    }
    if data is not None:
        report["data"] = data
    return report


def encode_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
