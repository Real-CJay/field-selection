from decimal import Decimal
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from api_server import (
    allocate_students,
    assign_competition_ranks,
    calculate_accuracy,
    calculate_average_gpa,
    require_admin,
)


def student(index, gpa, preferences, **grades):
    defaults = {
        "cse": 3.0,
        "maths": 3.0,
        "electrical": 3.0,
        "fluids": 3.0,
        "mechanics": 3.0,
        "material": 3.0,
    }
    defaults.update(grades)
    return {
        "index": index,
        "name": index,
        "average_gpa": Decimal(gpa),
        "preferences": preferences,
        **defaults,
    }


def test_calculates_credit_weighted_gpa_to_four_decimals():
    result = calculate_average_gpa(
        {
            "cse": 4,
            "maths": 3.7,
            "electrical": 3.3,
            "fluids": 3,
            "mechanics": 2.7,
            "material": 2.3,
        }
    )
    assert result == Decimal("3.2643")


def test_assigns_shared_competition_ranks_without_module_tiebreakers():
    students = [
        student("C", "3.5000", ["computer"]),
        student("A", "4.0000", ["computer"]),
        student("B", "3.5000", ["computer"], cse=4),
        student("D", "3.0000", ["computer"]),
    ]
    assign_competition_ranks(students)
    assert {item["index"]: item["student_rank"] for item in students} == {
        "A": 1,
        "B": 2,
        "C": 2,
        "D": 4,
    }


def test_uncontested_students_receive_their_requested_department():
    students = [
        student("A", "4.0000", ["computer", "civil"]),
        student("B", "4.0000", ["civil", "computer"]),
    ]
    cutoffs, processed = allocate_students(students, {"computer": 1, "civil": 1})
    assert {item["index"]: item["assigned_dept"] for item in processed} == {
        "A": "computer",
        "B": "civil",
    }
    assert cutoffs == {"computer": Decimal("4.0000"), "civil": Decimal("4.0000")}


def test_tiebreaker_is_used_only_when_a_department_is_contested():
    students = [
        student("A", "3.5000", ["computer", "civil"], cse=4, maths=4),
        student("B", "3.5000", ["computer", "civil"], cse=3, maths=3),
    ]
    _, processed = allocate_students(students, {"computer": 1, "civil": 1})
    assert {item["index"]: item["assigned_dept"] for item in processed} == {
        "A": "computer",
        "B": "civil",
    }


def test_exact_tie_uses_index_number_and_loser_advances():
    students = [
        student("250002E", "3.5000", ["computer", "civil"]),
        student("250001E", "3.5000", ["computer", "civil"]),
    ]
    _, processed = allocate_students(students, {"computer": 1, "civil": 1})
    assert {item["index"]: item["assigned_dept"] for item in processed} == {
        "250001E": "computer",
        "250002E": "civil",
    }


def test_full_department_is_skipped_for_lower_gpa_students():
    students = [
        student("A", "4.0000", ["computer", "civil"]),
        student("B", "3.0000", ["computer", "civil"]),
    ]
    cutoffs, processed = allocate_students(students, {"computer": 1, "civil": 1})
    assert {item["index"]: item["assigned_dept"] for item in processed} == {
        "A": "computer",
        "B": "civil",
    }
    assert cutoffs["civil"] == Decimal("3.0000")


def test_accuracy_is_one_decimal_and_capped_at_one_hundred():
    assert calculate_accuracy(7) == 0.9
    assert calculate_accuracy(743) == 100
    assert calculate_accuracy(800) == 100


def test_admin_credentials_are_checked_server_side(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "CJay")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin")
    assert require_admin(HTTPBasicCredentials(username="CJay", password="admin")) == "CJay"

    with pytest.raises(HTTPException) as error:
        require_admin(HTTPBasicCredentials(username="CJay", password="wrong"))
    assert error.value.status_code == 401
