from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from itertools import combinations
from math import comb
import os
import re
import secrets
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Path, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from supabase import Client, create_client

load_dotenv()

app = FastAPI(title="Field Selection Allocation API")

frontend_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_URL", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

BASE_QUOTAS = {
    "biomedical": 15,
    "chemical": 78,
    "civil": 125,
    "electrical": 90,
    "computer": 200,
    "electronic": 100,
    "mechanical": 80,
    "material": 45,
    "aeronautical": 10,
    "mechatronics": 10,
}

TIEBREAKER_RULES = {
    "biomedical": ("electrical", "maths"),
    "chemical": ("mechanics", "maths"),
    "civil": ("fluids", "mechanics"),
    "computer": ("cse", "maths"),
    "electrical": ("electrical", "maths"),
    "electronic": ("electrical", "maths"),
    "material": ("material", "mechanics"),
    "mechanical": ("mechanics", "maths"),
    "aeronautical": ("mechanics", "maths"),
    "mechatronics": ("mechanics", "maths"),
}

SUBJECT_CREDITS = {
    "cse": Decimal("3"),
    "maths": Decimal("3"),
    "electrical": Decimal("2"),
    "fluids": Decimal("2"),
    "mechanics": Decimal("2"),
    "material": Decimal("2"),
}

DISPLAY_GPA_PRECISION = Decimal("0.0001")
ALLOCATION_GPA_PRECISION = Decimal("0.01")
TOTAL_COHORT = 743
DEFAULT_ALLOCATION_STATE_LIMIT = 10_000
CORRECTABLE_MODULES = {"cse", "maths", "electrical", "material"}
GRADE_VALUES = {
    "A+": 4.0, "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7, "D": 1.0, "F": 0.0,
}
GRADE_LABELS = {
    4.0: "A / A+", 3.7: "A-", 3.3: "B+", 3.0: "B", 2.7: "B-",
    2.3: "C+", 2.0: "C", 1.7: "C-", 1.0: "D", 0.0: "F",
}
GRADE_LABEL_VALUES = set(GRADE_LABELS.values())
security = HTTPBasic()


@dataclass(frozen=True)
class AllocationState:
    remaining: tuple[tuple[str, int], ...]
    assignments: tuple[tuple[str, str | None], ...]
    cutoffs: tuple[tuple[str, Decimal | None], ...]

    def remaining_dict(self) -> dict[str, int]:
        return dict(self.remaining)

    def assignments_dict(self) -> dict[str, str | None]:
        return dict(self.assignments)

    def cutoffs_dict(self) -> dict[str, Decimal | None]:
        return dict(self.cutoffs)


class CorrectionRequestInput(BaseModel):
    index_number: str
    module: str
    requested_grade: str


class CorrectionDecisionInput(BaseModel):
    decision: str


class AdminGradeUpdateInput(BaseModel):
    cse: str | None = None
    maths: str | None = None
    electrical: str | None = None
    fluids: str | None = None
    mechanics: str | None = None
    material: str | None = None


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    expected_username = os.environ.get("ADMIN_USERNAME")
    expected_password = os.environ.get("ADMIN_PASSWORD")
    valid = bool(expected_username and expected_password)
    if valid:
        valid = secrets.compare_digest(credentials.username, expected_username) and secrets.compare_digest(
            credentials.password, expected_password
        )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def grade_label(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        return GRADE_LABELS.get(float(value), "Not available")
    except (TypeError, ValueError):
        return "Not available"


def normalize_grade_label(value: Any) -> str:
    if isinstance(value, str) and value in GRADE_LABEL_VALUES:
        return value
    return grade_label(value)


def grade_value_from_label(value: Any) -> float:
    label = normalize_grade_label(value)
    if label == "A / A+":
        return 4.0
    if label in GRADE_VALUES:
        return GRADE_VALUES[label]
    raise ValueError("The original grade is not available, so this request cannot be reverted.")


def is_legacy_numeric_grade_error(error: Exception) -> bool:
    detail = str(error).lower()
    return "22p02" in detail or "invalid input syntax for type numeric" in detail


def is_legacy_status_constraint_error(error: Exception) -> bool:
    detail = str(error).lower()
    return "23514" in detail and "status" in detail


def as_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def calculate_average_gpa(results: dict[str, Any]) -> Decimal:
    missing = [subject for subject in SUBJECT_CREDITS if results.get(subject) is None]
    if missing:
        raise ValueError(f"Missing module results: {', '.join(missing)}")

    weighted_total = sum(
        as_decimal(results[subject]) * credit
        for subject, credit in SUBJECT_CREDITS.items()
    )
    total_credits = sum(SUBJECT_CREDITS.values())
    return (weighted_total / total_credits).quantize(
        DISPLAY_GPA_PRECISION, rounding=ROUND_HALF_UP
    )


def calculate_allocation_gpa(display_gpa: Decimal) -> Decimal:
    return display_gpa.quantize(ALLOCATION_GPA_PRECISION, rounding=ROUND_HALF_UP)


def calculate_tiebreaker(student: dict[str, Any], department: str) -> Decimal:
    subjects = TIEBREAKER_RULES[department]
    total = sum(
        as_decimal(student[subject]) * SUBJECT_CREDITS[subject]
        for subject in subjects
    )
    credits = sum(SUBJECT_CREDITS[subject] for subject in subjects)
    return total / credits


def assign_competition_ranks(students: list[dict[str, Any]]) -> None:
    ordered = sorted(students, key=lambda student: (-student["average_gpa"], student["index"]))
    previous_gpa: Decimal | None = None
    current_rank = 0

    for position, student in enumerate(ordered, start=1):
        if student["average_gpa"] != previous_gpa:
            current_rank = position
            previous_gpa = student["average_gpa"]
        student["student_rank"] = current_rank


def _freeze_state(
    remaining: dict[str, int],
    assignments: dict[str, str | None],
    cutoffs: dict[str, Decimal | None],
) -> AllocationState:
    return AllocationState(
        tuple(sorted(remaining.items())),
        tuple(sorted(assignments.items())),
        tuple(sorted(cutoffs.items())),
    )


def _winner_options(
    contenders: list[dict[str, Any]], department: str, seats: int, option_limit: int
) -> tuple[list[set[str]], bool]:
    if seats <= 0:
        return [set()], False
    if len(contenders) <= seats:
        return [{student["index"] for student in contenders}], False

    by_score: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
    for student in contenders:
        by_score[calculate_tiebreaker(student, department)].append(student)

    guaranteed: set[str] = set()
    seats_left = seats
    for score in sorted(by_score, reverse=True):
        group = by_score[score]
        if len(group) <= seats_left:
            guaranteed.update(student["index"] for student in group)
            seats_left -= len(group)
            if seats_left == 0:
                return [guaranteed], False
            continue

        if comb(len(group), seats_left) > option_limit:
            return [], True
        return [
            guaranteed | set(choice)
            for choice in combinations(sorted(student["index"] for student in group), seats_left)
        ], False
    return [guaranteed], False


def _process_gpa_group(
    base_state: AllocationState,
    group: list[dict[str, Any]],
    departments: list[str],
    state_budget: int,
) -> tuple[list[AllocationState], bool]:
    students = {student["index"]: student for student in group}
    initial = (
        base_state.remaining_dict(),
        base_state.assignments_dict(),
        base_state.cutoffs_dict(),
        {index: 0 for index in students},
        set(students),
    )
    active = [initial]
    all_completed: set[AllocationState] = set()

    while active:
        completed: list[AllocationState] = []
        next_round: list[tuple[Any, ...]] = []
        for remaining, assignments, cutoffs, positions, unassigned in active:
            requests: dict[str, list[dict[str, Any]]] = defaultdict(list)
            still_unassigned = set(unassigned)
            next_positions = dict(positions)
            for index in list(still_unassigned):
                student = students[index]
                position = next_positions[index]
                while position < len(student["preferences"]) and remaining.get(
                    student["preferences"][position], 0
                ) <= 0:
                    position += 1
                next_positions[index] = position
                if position >= len(student["preferences"]):
                    still_unassigned.remove(index)
                    assignments[index] = None
                else:
                    requests[student["preferences"][position]].append(student)

            if not requests:
                completed.append(_freeze_state(remaining, assignments, cutoffs))
                continue

            branches = [(remaining, assignments, cutoffs, next_positions, still_unassigned)]
            for department in departments:
                contenders = requests.get(department, [])
                if not contenders:
                    continue
                expanded: list[tuple[Any, ...]] = []
                for branch_remaining, branch_assignments, branch_cutoffs, branch_positions, branch_unassigned in branches:
                    option_limit = max(
                        0,
                        state_budget
                        - len(all_completed)
                        - len(expanded)
                        - len(next_round)
                        - len(completed),
                    )
                    options, option_overflow = _winner_options(
                        contenders,
                        department,
                        branch_remaining.get(department, 0),
                        option_limit,
                    )
                    if option_overflow:
                        return [], True
                    for winner_indexes in options:
                        new_remaining = dict(branch_remaining)
                        new_assignments = dict(branch_assignments)
                        new_cutoffs = dict(branch_cutoffs)
                        new_positions = dict(branch_positions)
                        new_unassigned = set(branch_unassigned)
                        for contender in contenders:
                            index = contender["index"]
                            if index in winner_indexes:
                                new_assignments[index] = department
                                new_unassigned.discard(index)
                                new_remaining[department] -= 1
                                new_cutoffs[department] = contender["allocation_gpa"]
                            else:
                                new_positions[index] += 1
                        expanded.append(
                            (new_remaining, new_assignments, new_cutoffs, new_positions, new_unassigned)
                        )
                        if (
                            len(all_completed)
                            + len(expanded)
                            + len(next_round)
                            + len(completed)
                            > state_budget
                        ):
                            return [], True
                branches = expanded

            for branch in branches:
                if branch[4]:
                    next_round.append(branch)
                else:
                    completed.append(_freeze_state(branch[0], branch[1], branch[2]))

        all_completed.update(completed)
        if not next_round:
            return list(all_completed), False
        if len(all_completed) + len(next_round) > state_budget:
            return [], True
        active = next_round

    return list(all_completed), False


def allocate_students(
    students: list[dict[str, Any]],
    quotas: dict[str, int],
    state_limit: int = DEFAULT_ALLOCATION_STATE_LIMIT,
) -> tuple[list[AllocationState], list[dict[str, Any]], Decimal | None]:
    assign_competition_ranks(students)
    ordered = sorted(students, key=lambda student: (-student["allocation_gpa"], student["index"]))
    initial = _freeze_state(
        quotas.copy(),
        {student["index"]: None for student in ordered},
        {department: None for department in quotas},
    )
    states = [initial]
    groups: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
    for student in ordered:
        groups[student["allocation_gpa"]].append(student)

    for allocation_gpa in sorted(groups, reverse=True):
        before_group = states
        expanded_states: set[AllocationState] = set()
        for state in before_group:
            results, overflow = _process_gpa_group(
                state,
                groups[allocation_gpa],
                list(quotas),
                max(1, state_limit - len(expanded_states)),
            )
            if overflow or len(expanded_states) + len(results) > state_limit:
                return before_group, ordered, allocation_gpa
            expanded_states.update(results)
        states = list(expanded_states)

    return states, ordered, None


def read_complete_preferences(raw: dict[str, Any]) -> list[str] | None:
    values = {department: raw.get(department) for department in BASE_QUOTAS}
    ranks = list(values.values())
    expected = list(range(1, len(BASE_QUOTAS) + 1))

    if any(not isinstance(rank, int) for rank in ranks) or sorted(ranks) != expected:
        return None
    return [
        department
        for department, _ in sorted(values.items(), key=lambda item: item[1])
    ]


def build_eligible_students(raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []

    for row in raw_data:
        result_relation = row.get("student_results")
        preference_relation = row.get("student_preferences")
        if not result_relation or not preference_relation:
            continue

        results = result_relation[0] if isinstance(result_relation, list) else result_relation
        preferences_raw = (
            preference_relation[0]
            if isinstance(preference_relation, list)
            else preference_relation
        )
        preferences = read_complete_preferences(preferences_raw)
        if not preferences:
            continue

        try:
            average_gpa = calculate_average_gpa(results)
        except (ValueError, TypeError):
            continue

        eligible.append(
            {
                "index": row["index_number"],
                "name": row["name"],
                "average_gpa": average_gpa,
                "allocation_gpa": calculate_allocation_gpa(average_gpa),
                "preferences": preferences,
                **{subject: results[subject] for subject in SUBJECT_CREDITS},
            }
        )

    return eligible


def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured.")
    return create_client(url, key)


def get_state_limit() -> int:
    try:
        configured = int(os.environ.get("ALLOCATION_STATE_LIMIT", DEFAULT_ALLOCATION_STATE_LIMIT))
        return min(DEFAULT_ALLOCATION_STATE_LIMIT, max(1, configured))
    except ValueError:
        return DEFAULT_ALLOCATION_STATE_LIMIT


def run_allocation_engine() -> tuple[list[AllocationState], list[dict[str, Any]], Decimal | None]:
    return allocate_students(load_eligible_students(), BASE_QUOTAS, get_state_limit())


def load_eligible_students() -> list[dict[str, Any]]:
    response = (
        get_supabase()
        .table("students")
        .select(
            "index_number, name, "
            "student_results(average_gpa, cse, electrical, fluids, maths, mechanics, material), "
            "student_preferences(biomedical, chemical, civil, computer, electrical, "
            "electronic, mechanical, material, aeronautical, mechatronics)"
        )
        .execute()
    )
    return build_eligible_students(response.data)


def aggregate_cutoffs(
    states: list[AllocationState], overflow_gpa: Decimal | None
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for department in states[0].cutoffs_dict():
        values = [state.cutoffs_dict()[department] for state in states]
        numeric = sorted({value for value in values if value is not None})
        open_possible = any(value is None for value in values)
        if not numeric:
            result[department] = {"status": "open", "incomplete": overflow_gpa is not None}
        elif len(numeric) == 1 and not open_possible:
            result[department] = {
                "status": "fixed",
                "value": float(numeric[0]),
                "incomplete": overflow_gpa is not None,
            }
        else:
            result[department] = {
                "status": "range",
                "min": float(numeric[0]),
                "max": float(numeric[-1]),
                "open_possible": open_possible,
                "incomplete": overflow_gpa is not None,
            }
    return result


def aggregate_student_result(
    student: dict[str, Any],
    states: list[AllocationState],
    overflow_gpa: Decimal | None,
) -> dict[str, Any]:
    if overflow_gpa is not None and student["allocation_gpa"] <= overflow_gpa:
        return {
            "allocation_status": "unresolved",
            "assigned_department": None,
            "possible_departments": [],
            "border_departments": [],
            "guaranteed_department": None,
            "allocation_explanation": (
                "Your estimate cannot be narrowed further because linked grade ties create too "
                "many valid outcomes. Subject marks are required to resolve this boundary."
            ),
        }

    outcomes = {state.assignments_dict().get(student["index"]) for state in states}
    departments = [department for department in student["preferences"] if department in outcomes]
    includes_unplaced = None in outcomes
    if len(outcomes) == 1 and not includes_unplaced:
        return {
            "allocation_status": "certain",
            "assigned_department": departments[0],
            "possible_departments": departments,
            "border_departments": [],
            "guaranteed_department": departments[0],
            "allocation_explanation": None,
        }

    guaranteed = departments[-1] if departments and not includes_unplaced else None
    border_departments = departments[:-1] if guaranteed else departments
    if guaranteed:
        explanation = (
            "Your placement is on the allocation border for one or more higher preferences. "
            f"You are guaranteed {guaranteed} or a higher-ranked preference."
        )
    else:
        explanation = (
            "Your placement is on an unresolved allocation border and no department can yet be "
            "guaranteed without subject marks."
        )
    return {
        "allocation_status": "border",
        "assigned_department": None,
        "possible_departments": departments,
        "border_departments": border_departments,
        "guaranteed_department": guaranteed,
        "allocation_explanation": explanation,
    }


def aggregate_department_gpas(
    department: str,
    states: list[AllocationState],
    students: list[dict[str, Any]],
    overflow_gpa: Decimal | None,
) -> list[dict[str, Any]]:
    gpas = sorted({student["allocation_gpa"] for student in students}, reverse=True)
    state_counts: list[dict[Decimal, int]] = []
    student_by_index = {student["index"]: student for student in students}
    for state in states:
        counts: dict[Decimal, int] = defaultdict(int)
        for index, assigned in state.assignments:
            if assigned == department:
                counts[student_by_index[index]["allocation_gpa"]] += 1
        state_counts.append(counts)

    groups = []
    for gpa in gpas:
        if overflow_gpa is not None and gpa <= overflow_gpa:
            continue
        counts = [state.get(gpa, 0) for state in state_counts]
        if max(counts, default=0) == 0:
            continue
        groups.append({
            "gpa": float(gpa),
            "min_count": min(counts),
            "max_count": max(counts),
        })
    return groups


def aggregate_admin_departments(
    states: list[AllocationState],
    students: list[dict[str, Any]],
    overflow_gpa: Decimal | None,
    quotas: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Build an admin-only view of department membership across allocation states."""
    quotas = quotas or BASE_QUOTAS
    state_total = len(states)
    cutoffs = aggregate_cutoffs(states, overflow_gpa)
    assignment_counts: dict[str, dict[str, int]] = {
        department: defaultdict(int) for department in quotas
    }
    selected_counts: dict[str, list[int]] = {
        department: [] for department in quotas
    }

    for state in states:
        per_department = defaultdict(int)
        for index, department in state.assignments:
            if department is None:
                continue
            assignment_counts[department][index] += 1
            per_department[department] += 1
        for department in quotas:
            selected_counts[department].append(per_department[department])

    departments = []
    for department, quota in quotas.items():
        cutoff = cutoffs[department]
        boundary_gpas: set[Decimal] = set()
        if cutoff["status"] == "fixed":
            boundary_gpas.add(as_decimal(cutoff["value"]))
        elif cutoff["status"] == "range":
            boundary_gpas.update((as_decimal(cutoff["min"]), as_decimal(cutoff["max"])))

        rule = TIEBREAKER_RULES[department]
        candidates_by_gpa: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
        for student in students:
            if department in student["preferences"]:
                candidates_by_gpa[student["allocation_gpa"]].append(student)

        rows = []
        for student in students:
            selected_state_count = assignment_counts[department].get(student["index"], 0)
            if selected_state_count == 0:
                continue

            same_gpa_candidates = candidates_by_gpa[student["allocation_gpa"]]
            is_boundary_tie = (
                student["allocation_gpa"] in boundary_gpas
                and len(same_gpa_candidates) > 1
            )
            tiebreaker = None
            if is_boundary_tie:
                score = calculate_tiebreaker(student, department)
                matching_scores = sum(
                    calculate_tiebreaker(candidate, department) == score
                    for candidate in same_gpa_candidates
                )
                tiebreaker = {
                    "subjects": [
                        {
                            "subject": subject,
                            "grade": grade_label(student[subject]),
                            "value": float(student[subject]),
                        }
                        for subject in rule
                    ],
                    "score": round(float(score), 4),
                    "candidate_count": len(same_gpa_candidates),
                    "score_tied": matching_scores > 1,
                }

            rows.append({
                "index_number": student["index"],
                "name": student["name"],
                "average_gpa": float(student["average_gpa"]),
                "allocation_gpa": float(student["allocation_gpa"]),
                "selection_status": (
                    "selected" if selected_state_count == state_total else "border"
                ),
                "selected_state_count": selected_state_count,
                "total_states": state_total,
                "tiebreaker": tiebreaker,
            })

        rows.sort(key=lambda row: (-row["allocation_gpa"], row["index_number"]))
        counts = selected_counts[department]
        departments.append({
            "department": department,
            "quota": quota,
            "selected_min": min(counts, default=0),
            "selected_max": max(counts, default=0),
            "cutoff": cutoff,
            "incomplete": overflow_gpa is not None,
            "students": rows,
        })
    return departments


def parse_lookup_gpa(value: str) -> Decimal:
    if not re.fullmatch(r"(?:[0-3]\.\d{2}|4\.00)", value):
        raise HTTPException(
            status_code=422,
            detail="GPA must be written with two decimal places from 0.00 to 4.00.",
        )
    return as_decimal(value)


def aggregate_gpa_lookup(
    target_gpa: Decimal,
    states: list[AllocationState],
    students: list[dict[str, Any]],
    overflow_gpa: Decimal | None,
    quotas: dict[str, int] | None = None,
) -> dict[str, Any]:
    matching = [student for student in students if student["allocation_gpa"] == target_gpa]

    outcome_counts: dict[tuple[Any, ...], int] = defaultdict(int)
    for student in matching:
        outcome = aggregate_student_result(student, states, overflow_gpa)
        key = (
            outcome["allocation_status"],
            outcome["assigned_department"],
            tuple(outcome["possible_departments"]),
            tuple(outcome["border_departments"]),
            outcome["guaranteed_department"],
        )
        outcome_counts[key] += 1

    allocation_groups = [
        {
            "allocation_status": key[0],
            "assigned_department": key[1],
            "possible_departments": list(key[2]),
            "border_departments": list(key[3]),
            "guaranteed_department": key[4],
            "count": count,
        }
        for key, count in sorted(
            outcome_counts.items(),
            key=lambda item: (-item[1], str(item[0])),
        )
    ]

    matching_indexes = {student["index"] for student in matching}
    tie_counts: dict[tuple[Any, ...], int] = defaultdict(int)
    for department in aggregate_admin_departments(
        states, students, overflow_gpa, quotas
    ):
        for student in department["students"]:
            if student["index_number"] not in matching_indexes or not student["tiebreaker"]:
                continue
            tiebreaker = student["tiebreaker"]
            subjects = tuple(
                (subject["subject"], subject["grade"], subject["value"])
                for subject in tiebreaker["subjects"]
            )
            key = (
                department["department"],
                subjects,
                tiebreaker["score"],
                tiebreaker["candidate_count"],
                tiebreaker["score_tied"],
                student["selection_status"],
            )
            tie_counts[key] += 1

    tiebreak_groups = [
        {
            "department": key[0],
            "subjects": [
                {"subject": subject[0], "grade": subject[1], "value": subject[2]}
                for subject in key[1]
            ],
            "score": key[2],
            "candidate_count": key[3],
            "score_tied": key[4],
            "selection_status": key[5],
            "count": count,
        }
        for key, count in sorted(
            tie_counts.items(),
            key=lambda item: (item[0][0], -item[0][2], item[0][1]),
        )
    ]

    return {
        "gpa": float(target_gpa),
        "count": len(matching),
        "total_students_processed": len(students),
        "allocation_groups": allocation_groups,
        "tiebreak_groups": tiebreak_groups,
    }


def calculate_accuracy(total_students: int) -> float:
    return round(min(100, total_students / TOTAL_COHORT * 100), 1)


@app.get("/api/cutoffs")
def get_estimated_cutoffs() -> dict[str, Any]:
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            "total_students_processed": len(students),
            "accuracy_percentage": calculate_accuracy(len(students)),
            "cutoffs": aggregate_cutoffs(states, overflow_gpa),
            "allocation_incomplete": overflow_gpa is not None,
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/gpa-lookup")
def get_gpa_lookup(gpa: str) -> dict[str, Any]:
    target_gpa = parse_lookup_gpa(gpa)
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            **aggregate_gpa_lookup(target_gpa, states, students, overflow_gpa),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/allocation/{index_number}")
def get_student_allocation(
    index_number: str = Path(..., title="The student's index number"),
) -> dict[str, Any]:
    try:
        states, students, overflow_gpa = run_allocation_engine()
        target = next(
            (student for student in students if student["index"] == index_number), None
        )
        if not target:
            raise HTTPException(
                status_code=404,
                detail="Student not found or has incomplete results/preferences.",
            )

        allocation = aggregate_student_result(target, states, overflow_gpa)
        return {
            "status": "success",
            "index_number": target["index"],
            "name": target["name"],
            **allocation,
            "average_gpa": float(target["average_gpa"]),
            "allocation_gpa": float(target["allocation_gpa"]),
            "student_rank": target["student_rank"],
            "cutoffs": aggregate_cutoffs(states, overflow_gpa),
            "total_students_processed": len(students),
            "accuracy_percentage": calculate_accuracy(len(students)),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/departments/{department}/gpas")
def get_department_gpas(department: str) -> dict[str, Any]:
    if department not in BASE_QUOTAS:
        raise HTTPException(status_code=404, detail="Department was not found.")
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            "department": department,
            "groups": aggregate_department_gpas(
                department, states, students, overflow_gpa
            ),
            "incomplete": overflow_gpa is not None,
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/admin/login")
def admin_login(username: str = Depends(require_admin)) -> dict[str, str]:
    return {"status": "success", "username": username}


@app.get("/api/admin/departments")
def list_admin_departments(_: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            "departments": aggregate_admin_departments(states, students, overflow_gpa),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/admin/students")
def list_admin_students(_: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        response = (
            get_supabase()
            .table("students")
            .select(
                "index_number,name,"
                "student_results(average_gpa,cse,electrical,fluids,maths,mechanics,material),"
                "student_preferences(biomedical,chemical,civil,computer,electrical,electronic,"
                "mechanical,material,aeronautical,mechatronics,submitted_at)"
            )
            .order("index_number")
            .execute()
        )
        states, eligible, overflow_gpa = run_allocation_engine()
        allocation_by_index = {
            student["index"]: aggregate_student_result(student, states, overflow_gpa)
            for student in eligible
        }
        rows = []
        for row in response.data:
            raw_results = row.get("student_results")
            results = raw_results[0] if isinstance(raw_results, list) and raw_results else raw_results
            raw_preferences = row.get("student_preferences")
            preferences = (
                raw_preferences[0]
                if isinstance(raw_preferences, list) and raw_preferences
                else raw_preferences
            )
            display_gpa = None
            if results:
                try:
                    display_gpa = float(calculate_average_gpa(results))
                except (ValueError, TypeError):
                    display_gpa = None
            rows.append({
                "index_number": row["index_number"],
                "name": row["name"],
                "average_gpa": display_gpa,
                "grades": {
                    subject: grade_label(results.get(subject) if results else None)
                    for subject in SUBJECT_CREDITS
                },
                "preferences": read_complete_preferences(preferences) if preferences else [],
                "submitted_at": preferences.get("submitted_at") if preferences else None,
                "allocation": allocation_by_index.get(row["index_number"], {
                    "allocation_status": "incomplete",
                    "assigned_department": None,
                    "possible_departments": [],
                    "border_departments": [],
                    "guaranteed_department": None,
                }),
            })
        return {"status": "success", "students": rows}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.patch("/api/admin/students/{index_number}/grades")
def update_admin_student_grades(
    update: AdminGradeUpdateInput,
    index_number: str,
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    submitted = update.model_dump(exclude_none=True)
    if not submitted:
        raise HTTPException(status_code=422, detail="At least one grade is required.")
    invalid = {subject: grade for subject, grade in submitted.items() if grade not in GRADE_VALUES}
    if invalid:
        raise HTTPException(status_code=422, detail="One or more grades are invalid.")

    try:
        database = get_supabase()
        current_response = (
            database.table("student_results")
            .select("index_number,cse,electrical,fluids,maths,mechanics,material")
            .eq("index_number", index_number)
            .maybe_single()
            .execute()
        )
        if not current_response.data:
            raise HTTPException(status_code=404, detail="Student results were not found.")

        numeric_updates = {
            subject: GRADE_VALUES[grade] for subject, grade in submitted.items()
        }
        merged = {**current_response.data, **numeric_updates}
        numeric_updates["average_gpa"] = float(calculate_average_gpa(merged))
        database.table("student_results").update(numeric_updates).eq(
            "index_number", index_number
        ).execute()

        for subject in submitted:
            reviewed_at = datetime.now(timezone.utc).isoformat()
            pending_request = (
                database.table("grade_correction_requests")
                .update({"status": "superseded", "reviewed_at": reviewed_at})
                .eq("index_number", index_number)
                .eq("module", subject)
                .eq("status", "pending")
            )
            try:
                pending_request.execute()
            except Exception as error:
                # Compatibility until the prepared status migration is applied.
                if not is_legacy_status_constraint_error(error):
                    raise
                database.table("grade_correction_requests").update({
                    "status": "rejected", "reviewed_at": reviewed_at
                }).eq("index_number", index_number).eq("module", subject).eq(
                    "status", "pending"
                ).execute()

        return {"status": "success", "average_gpa": numeric_updates["average_gpa"]}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/api/correction-requests", status_code=status.HTTP_201_CREATED)
def create_correction_request(request: CorrectionRequestInput) -> dict[str, Any]:
    module = request.module.strip().lower()
    grade = request.requested_grade.strip().upper()
    if module not in CORRECTABLE_MODULES or grade not in GRADE_VALUES:
        raise HTTPException(status_code=422, detail="Invalid module or requested grade.")

    try:
        database = get_supabase()
        result = (
            database.table("student_results")
            .select(f"index_number,{module}")
            .eq("index_number", request.index_number)
            .maybe_single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Student results were not found.")

        existing = (
            database.table("grade_correction_requests")
            .select("id")
            .eq("index_number", request.index_number)
            .eq("module", module)
            .eq("status", "pending")
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="A pending request already exists for this module.")

        payload = {
            "index_number": request.index_number,
            "module": module,
            "current_grade": grade_label(result.data.get(module)),
            "requested_grade": grade,
            "status": "pending",
        }
        try:
            created = database.table("grade_correction_requests").insert(payload).execute()
        except Exception as error:
            # Compatibility with the old numeric current_grade column until migration.
            if not is_legacy_numeric_grade_error(error):
                raise
            payload["current_grade"] = result.data.get(module)
            created = database.table("grade_correction_requests").insert(payload).execute()
        created_request = dict(created.data[0]) if created.data else None
        if created_request:
            created_request["current_grade"] = normalize_grade_label(
                created_request.get("current_grade")
            )
        return {"status": "success", "request": created_request}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/admin/correction-requests")
def list_correction_requests(_: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        database = get_supabase()
        try:
            response = (
                database.table("grade_correction_requests")
                .select("id,index_number,module,current_grade,requested_grade,status,created_at,reviewed_at,reverted_at")
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as error:
            if "reverted_at" not in str(error).lower():
                raise
            response = (
                database.table("grade_correction_requests")
                .select("id,index_number,module,current_grade,requested_grade,status,created_at,reviewed_at")
                .order("created_at", desc=True)
                .execute()
            )
        requests = []
        for request in response.data:
            normalized = dict(request)
            normalized["current_grade"] = normalize_grade_label(
                normalized.get("current_grade")
            )
            normalized.setdefault("reverted_at", None)
            requests.append(normalized)
        return {"status": "success", "requests": requests}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/api/admin/correction-requests/{request_id}/revert")
def revert_correction_request(
    request_id: int = Path(..., ge=1),
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    try:
        database = get_supabase()
        response = (
            database.table("grade_correction_requests")
            .select("id,index_number,module,current_grade,requested_grade,status")
            .eq("id", request_id)
            .maybe_single()
            .execute()
        )
        correction = response.data
        if not correction:
            raise HTTPException(status_code=404, detail="Correction request was not found.")
        if correction["status"] != "approved":
            raise HTTPException(status_code=409, detail="Only an approved correction can be reverted.")

        results_response = (
            database.table("student_results")
            .select("index_number,cse,electrical,fluids,maths,mechanics,material")
            .eq("index_number", correction["index_number"])
            .maybe_single()
            .execute()
        )
        current_results = results_response.data
        if not current_results:
            raise HTTPException(status_code=404, detail="Student results were not found.")

        module = correction["module"]
        approved_value = GRADE_VALUES[correction["requested_grade"]]
        if abs(float(current_results[module]) - approved_value) > 0.00001:
            raise HTTPException(
                status_code=409,
                detail="This grade changed after the correction was approved, so the older correction cannot safely be reverted.",
            )

        original_value = grade_value_from_label(correction["current_grade"])
        changed_results = {**current_results, module: original_value}
        average_gpa = float(calculate_average_gpa(changed_results))
        database.table("student_results").update({
            module: original_value,
            "average_gpa": average_gpa,
        }).eq("index_number", correction["index_number"]).execute()
        database.table("grade_correction_requests").update({
            "status": "reverted",
            "reverted_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", request_id).eq("status", "approved").execute()
        return {"status": "success", "average_gpa": average_gpa}
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.patch("/api/admin/correction-requests/{request_id}")
def review_correction_request(
    decision: CorrectionDecisionInput,
    request_id: int = Path(..., ge=1),
    _: str = Depends(require_admin),
) -> dict[str, Any]:
    if decision.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Decision must be approved or rejected.")

    try:
        database = get_supabase()
        response = (
            database.table("grade_correction_requests")
            .select("id,index_number,module,requested_grade,status")
            .eq("id", request_id)
            .maybe_single()
            .execute()
        )
        correction = response.data
        if not correction:
            raise HTTPException(status_code=404, detail="Correction request was not found.")
        if correction["status"] != "pending":
            raise HTTPException(status_code=409, detail="This request has already been reviewed.")

        if decision.decision == "approved":
            results_response = (
                database.table("student_results")
                .select("index_number,cse,electrical,fluids,maths,mechanics,material")
                .eq("index_number", correction["index_number"])
                .maybe_single()
                .execute()
            )
            if not results_response.data:
                raise HTTPException(status_code=404, detail="Student results were not found.")
            changed_results = {
                **results_response.data,
                correction["module"]: GRADE_VALUES[correction["requested_grade"]],
            }
            database.table("student_results").update({
                correction["module"]: changed_results[correction["module"]],
                "average_gpa": float(calculate_average_gpa(changed_results)),
            }).eq("index_number", correction["index_number"]).execute()

        reviewed_at = datetime.now(timezone.utc).isoformat()
        database.table("grade_correction_requests").update({
            "status": decision.decision,
            "reviewed_at": reviewed_at,
        }).eq("id", request_id).execute()
        return {"status": "success", "decision": decision.decision}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
