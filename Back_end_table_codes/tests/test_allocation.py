from decimal import Decimal
import json
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from api_server import (
    aggregate_admin_departments,
    aggregate_cutoffs,
    aggregate_department_gpas,
    aggregate_gpa_lookup,
    aggregate_student_result,
    allocate_students,
    assign_competition_ranks,
    calculate_accuracy,
    calculate_allocation_gpa,
    calculate_average_gpa,
    calculate_tiebreaker,
    get_state_limit,
    grade_label,
    grade_value_from_label,
    normalize_grade_label,
    parse_lookup_gpa,
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
        "allocation_gpa": calculate_allocation_gpa(Decimal(gpa)),
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
    assert calculate_allocation_gpa(result) == Decimal("3.26")
    assert calculate_allocation_gpa(Decimal("3.2650")) == Decimal("3.27")


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
    states, processed, overflow = allocate_students(students, {"computer": 1, "civil": 1})
    assert overflow is None
    assert states[0].assignments_dict() == {
        "A": "computer",
        "B": "civil",
    }
    assert states[0].cutoffs_dict() == {
        "computer": Decimal("4.00"), "civil": Decimal("4.00")
    }


def test_tiebreaker_is_used_only_when_a_department_is_contested():
    students = [
        student("A", "3.5000", ["computer", "civil"], cse=4, maths=4),
        student("B", "3.5000", ["computer", "civil"], cse=3, maths=3),
    ]
    states, _, _ = allocate_students(students, {"computer": 1, "civil": 1})
    assert states[0].assignments_dict() == {
        "A": "computer",
        "B": "civil",
    }


def test_tiebreaker_uses_credit_weighted_module_scores():
    mechanics_high = student(
        "A", "3.5000", ["mechanical"], mechanics=4.0, maths=2.7
    )
    balanced = student(
        "B", "3.5000", ["mechanical"], mechanics=3.3, maths=3.3
    )

    assert calculate_tiebreaker(mechanics_high, "mechanical") == Decimal("3.22")
    assert calculate_tiebreaker(balanced, "mechanical") == Decimal("3.3")
    states, _, _ = allocate_students(
        [mechanics_high, balanced], {"mechanical": 1}
    )
    assert states[0].assignments_dict() == {"A": None, "B": "mechanical"}


def test_mechanical_combined_score_can_outweigh_the_higher_mechanics_grade():
    mechanics_a = student(
        "A", "3.5000", ["mechanical"], mechanics=4.0, maths=2.0
    )
    stronger_combined = student(
        "B", "3.5000", ["mechanical"], mechanics=3.7, maths=4.0
    )

    states, _, _ = allocate_students(
        [mechanics_a, stronger_combined], {"mechanical": 1}
    )
    assert states[0].assignments_dict() == {"A": None, "B": "mechanical"}


def test_tiebreaker_is_not_used_across_different_two_decimal_gpas():
    higher_gpa = student(
        "A", "3.5100", ["computer"], cse=0.0, maths=0.0
    )
    lower_gpa = student(
        "B", "3.5000", ["computer"], cse=4.0, maths=4.0
    )

    states, _, _ = allocate_students([higher_gpa, lower_gpa], {"computer": 1})
    assert states[0].assignments_dict() == {"A": "computer", "B": None}


def test_exact_tie_branches_without_using_index_number():
    students = [
        student("250002E", "3.5000", ["computer", "civil"]),
        student("250001E", "3.5000", ["computer", "civil"]),
    ]
    states, processed, overflow = allocate_students(students, {"computer": 1, "civil": 1})
    assert overflow is None
    assert len(states) == 2
    result = aggregate_student_result(processed[0], states, overflow)
    assert result["allocation_status"] == "border"
    assert result["possible_departments"] == ["computer", "civil"]
    assert result["guaranteed_department"] == "civil"


def test_full_department_is_skipped_for_lower_gpa_students():
    students = [
        student("A", "4.0000", ["computer", "civil"]),
        student("B", "3.0000", ["computer", "civil"]),
    ]
    states, _, _ = allocate_students(students, {"computer": 1, "civil": 1})
    assert states[0].assignments_dict() == {
        "A": "computer",
        "B": "civil",
    }
    assert states[0].cutoffs_dict()["civil"] == Decimal("3.00")


def test_chained_ties_report_border_choices_and_guaranteed_fallback():
    preferences = ["electronic", "mechanical", "electrical"]
    students = [student(index, "3.5000", preferences) for index in ("A", "B", "C")]
    states, processed, overflow = allocate_students(
        students, {"electronic": 1, "mechanical": 1, "electrical": 1}
    )
    assert overflow is None
    result = aggregate_student_result(processed[0], states, overflow)
    assert result["border_departments"] == ["electronic", "mechanical"]
    assert result["guaranteed_department"] == "electrical"


def test_state_limit_marks_the_affected_gpa_suffix_unresolved():
    students = [
        student("A", "3.5000", ["computer", "civil"]),
        student("B", "3.5000", ["computer", "civil"]),
    ]
    states, processed, overflow = allocate_students(
        students, {"computer": 1, "civil": 1}, state_limit=1
    )
    assert overflow == Decimal("3.50")
    result = aggregate_student_result(processed[0], states, overflow)
    assert result["allocation_status"] == "unresolved"


def test_large_exact_tie_stops_before_generating_every_combination():
    students = [
        student(str(index), "3.5000", ["computer", "civil"])
        for index in range(20)
    ]
    states, _, overflow = allocate_students(
        students, {"computer": 10, "civil": 10}, state_limit=10
    )
    assert len(states) == 1
    assert overflow == Decimal("3.50")


def test_cutoffs_and_anonymous_department_groups_use_two_decimal_gpa():
    students = [
        student("A", "3.8250", ["computer", "civil"]),
        student("B", "3.8249", ["civil", "computer"]),
    ]
    states, processed, overflow = allocate_students(
        students, {"computer": 1, "civil": 1}
    )
    assert aggregate_cutoffs(states, overflow) == {
        "computer": {"status": "fixed", "value": 3.83, "incomplete": False},
        "civil": {"status": "fixed", "value": 3.82, "incomplete": False},
    }
    assert aggregate_department_gpas("computer", states, processed, overflow) == [
        {"gpa": 3.83, "min_count": 1, "max_count": 1}
    ]


def test_admin_department_view_lists_selected_students_and_boundary_tiebreakers():
    students = [
        student("A", "3.5000", ["computer", "civil"], cse=4, maths=4),
        student("B", "3.5000", ["computer", "civil"], cse=3, maths=3),
    ]
    states, processed, overflow = allocate_students(
        students, {"computer": 1, "civil": 1}
    )

    departments = aggregate_admin_departments(
        states, processed, overflow, {"computer": 1, "civil": 1}
    )
    computer = next(item for item in departments if item["department"] == "computer")

    assert computer["selected_min"] == computer["selected_max"] == 1
    assert [item["index_number"] for item in computer["students"]] == ["A"]
    assert computer["students"][0]["selection_status"] == "selected"
    assert computer["students"][0]["tiebreaker"] == {
        "subjects": [
            {"subject": "cse", "grade": "A / A+", "value": 4.0},
            {"subject": "maths", "grade": "A / A+", "value": 4.0},
        ],
        "score": 4.0,
        "candidate_count": 2,
        "score_tied": False,
    }


def test_admin_department_view_marks_exact_tie_students_as_border_outcomes():
    students = [
        student("A", "3.5000", ["computer", "civil"]),
        student("B", "3.5000", ["computer", "civil"]),
    ]
    states, processed, overflow = allocate_students(
        students, {"computer": 1, "civil": 1}
    )

    computer = next(
        item
        for item in aggregate_admin_departments(
            states, processed, overflow, {"computer": 1, "civil": 1}
        )
        if item["department"] == "computer"
    )
    assert {item["selection_status"] for item in computer["students"]} == {"border"}
    assert all(item["tiebreaker"]["score_tied"] for item in computer["students"])


def test_gpa_lookup_groups_allocations_and_tiebreaks_without_identities():
    students = [
        student("PRIVATE-A", "3.5000", ["computer", "civil"]),
        student("PRIVATE-B", "3.5000", ["computer", "civil"]),
        student("PRIVATE-C", "3.0000", ["civil", "computer"]),
    ]
    quotas = {"computer": 1, "civil": 2}
    states, processed, overflow = allocate_students(students, quotas)

    result = aggregate_gpa_lookup(
        Decimal("3.50"), states, processed, overflow, quotas
    )
    serialized = json.dumps(result)

    assert result["count"] == 2
    assert result["total_students_processed"] == 3
    assert result["allocation_groups"] == [{
        "allocation_status": "border",
        "assigned_department": None,
        "possible_departments": ["computer", "civil"],
        "border_departments": ["computer"],
        "guaranteed_department": "civil",
        "count": 2,
    }]
    assert any(
        group["department"] == "computer"
        and group["score_tied"]
        and group["count"] == 2
        for group in result["tiebreak_groups"]
    )
    assert "PRIVATE-A" not in serialized
    assert "PRIVATE-B" not in serialized
    assert '"name"' not in serialized
    assert '"index_number"' not in serialized


def test_gpa_lookup_returns_an_empty_private_result_for_no_matches():
    students = [student("PRIVATE-A", "3.5000", ["computer"])]
    states, processed, overflow = allocate_students(students, {"computer": 1})
    result = aggregate_gpa_lookup(
        Decimal("2.00"), states, processed, overflow, {"computer": 1}
    )
    assert result["count"] == 0
    assert result["allocation_groups"] == []
    assert result["tiebreak_groups"] == []


@pytest.mark.parametrize("value", ["3.5", "3.500", "-0.01", "4.01", "text"])
def test_gpa_lookup_requires_a_valid_two_decimal_value(value):
    with pytest.raises(HTTPException) as error:
        parse_lookup_gpa(value)
    assert error.value.status_code == 422


def test_gpa_lookup_accepts_the_valid_range_boundaries():
    assert parse_lookup_gpa("0.00") == Decimal("0.00")
    assert parse_lookup_gpa("4.00") == Decimal("4.00")


def test_grade_labels_are_letters_and_four_point_zero_remains_ambiguous():
    assert grade_label(4.0) == "A / A+"
    assert grade_label(3.3) == "B+"
    assert grade_label(None) == "Not available"
    assert normalize_grade_label("A / A+") == "A / A+"
    assert normalize_grade_label("3.3") == "B+"
    assert grade_value_from_label("A / A+") == 4.0
    assert grade_value_from_label("B+") == 3.3


def test_configured_state_limit_cannot_exceed_safety_cap(monkeypatch):
    monkeypatch.setenv("ALLOCATION_STATE_LIMIT", "999999")
    assert get_state_limit() == 10_000


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
