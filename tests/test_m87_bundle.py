from pathlib import Path

from vajra_space.bundle import validate_bundle_file


ROOT = Path(__file__).resolve().parents[1]


def test_m87_reference_bundle_integrity() -> None:
    result = validate_bundle_file(
        ROOT / "cases/m87-black-hole/evidence-bundle.json",
        ROOT / "schemas/bundle.schema.json",
    )
    assert result.valid, result.issues
