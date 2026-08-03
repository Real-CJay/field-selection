from pathlib import Path

import generate_student_recovery_codes as generator


def test_generated_code_has_sixteen_digits_and_safe_format(monkeypatch):
    values = iter(range(10))
    monkeypatch.setattr(
        generator.secrets,
        "randbelow",
        lambda _limit: next(values, 7),
    )
    monkeypatch.setattr(generator, "recovery_fingerprint", lambda code: f"hash:{code}")
    code, fingerprint = generator.generate_unique_code(set())
    assert len(code) == 16
    assert code.isdigit()
    assert generator.format_code(code).count("-") == 3
    assert fingerprint == f"hash:{code}"


def test_output_path_must_be_outside_repository(tmp_path):
    inside = generator.REPOSITORY_ROOT / "unsafe.recovery-codes.csv"
    try:
        generator.validated_output_path(inside)
        raise AssertionError("Expected repository output to be rejected.")
    except ValueError:
        pass

    output, temporary = generator.validated_output_path(
        tmp_path / "students.recovery-codes.csv"
    )
    assert output.parent == tmp_path.resolve()
    assert temporary.name.endswith(".tmp")


def test_csv_fields_are_neutralized_against_spreadsheet_formulas():
    assert generator.csv_safe("=cmd") == "'=cmd"
    assert generator.csv_safe("250544U") == "250544U"
