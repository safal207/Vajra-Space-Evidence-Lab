from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from vajra_space.evidence_card import (
    build_m87_reconstruction_card,
    render_evidence_card_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


def validate_card(card: dict, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(card),
        key=lambda item: list(item.absolute_path),
    )
    if not errors:
        return

    messages = []
    for error in errors:
        location = "$" if not error.absolute_path else "$." + ".".join(
            str(part) for part in error.absolute_path
        )
        messages.append("{}: {}".format(location, error.message))
    raise ValueError("Generated Evidence Card is invalid: " + "; ".join(messages))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=ROOT / "cases/m87-black-hole",
    )
    parser.add_argument(
        "--bundle-schema",
        type=Path,
        default=ROOT / "schemas/bundle.schema.json",
    )
    parser.add_argument(
        "--assessment-schema",
        type=Path,
        default=ROOT / "schemas/evidence-assessment.schema.json",
    )
    parser.add_argument(
        "--card-schema",
        type=Path,
        default=ROOT / "schemas/evidence-card.schema.json",
    )
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    card = build_m87_reconstruction_card(
        args.case_dir,
        bundle_schema_path=args.bundle_schema,
        assessment_schema_path=args.assessment_schema,
    )
    validate_card(card, args.card_schema)

    json_payload = json.dumps(
        card,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"
    markdown_payload = render_evidence_card_markdown(card)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json_payload, encoding="utf-8")
    args.markdown_output.write_text(markdown_payload, encoding="utf-8")

    print(json_payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
