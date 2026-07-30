from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
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
    allow_methods=["GET"],
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

GPA_PRECISION = Decimal("0.0001")
TOTAL_COHORT = 743


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
        GPA_PRECISION, rounding=ROUND_HALF_UP
    )


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


def allocate_students(
    students: list[dict[str, Any]], quotas: dict[str, int]
) -> tuple[dict[str, Decimal | None], list[dict[str, Any]]]:
    remaining_quotas = quotas.copy()
    cutoffs: dict[str, Decimal | None] = {department: None for department in quotas}

    assign_competition_ranks(students)
    ordered = sorted(students, key=lambda student: (-student["average_gpa"], student["index"]))

    for student in ordered:
        student["assigned_dept"] = None

    gpa_groups: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
    for student in ordered:
        gpa_groups[student["average_gpa"]].append(student)

    for gpa in sorted(gpa_groups, reverse=True):
        unassigned = {student["index"]: student for student in gpa_groups[gpa]}
        preference_positions = {index: 0 for index in unassigned}

        while unassigned:
            requests: dict[str, list[dict[str, Any]]] = defaultdict(list)
            exhausted: list[str] = []

            for index, student in unassigned.items():
                position = preference_positions[index]
                while (
                    position < len(student["preferences"])
                    and remaining_quotas.get(student["preferences"][position], 0) <= 0
                ):
                    position += 1
                preference_positions[index] = position

                if position >= len(student["preferences"]):
                    exhausted.append(index)
                else:
                    requests[student["preferences"][position]].append(student)

            for index in exhausted:
                unassigned.pop(index)

            if not requests:
                break

            for department in quotas:
                contenders = requests.get(department, [])
                if not contenders:
                    continue

                seats = remaining_quotas[department]
                if len(contenders) <= seats:
                    winners = sorted(contenders, key=lambda student: student["index"])
                else:
                    winners = sorted(
                        contenders,
                        key=lambda student: (
                            -calculate_tiebreaker(student, department),
                            student["index"],
                        ),
                    )[:seats]

                winner_indexes = {student["index"] for student in winners}
                for student in winners:
                    student["assigned_dept"] = department
                    remaining_quotas[department] -= 1
                    cutoffs[department] = gpa
                    unassigned.pop(student["index"], None)

                for student in contenders:
                    if student["index"] not in winner_indexes:
                        preference_positions[student["index"]] += 1

    return cutoffs, ordered


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


def run_allocation_engine() -> tuple[dict[str, Decimal | None], list[dict[str, Any]]]:
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
    return allocate_students(build_eligible_students(response.data), BASE_QUOTAS)


def serialize_cutoffs(cutoffs: dict[str, Decimal | None]) -> dict[str, float | None]:
    return {
        department: float(cutoff) if cutoff is not None else None
        for department, cutoff in cutoffs.items()
    }


def calculate_accuracy(total_students: int) -> float:
    return round(min(100, total_students / TOTAL_COHORT * 100), 1)


@app.get("/api/cutoffs")
def get_estimated_cutoffs() -> dict[str, Any]:
    try:
        cutoffs, students = run_allocation_engine()
        return {
            "status": "success",
            "total_students_processed": len(students),
            "accuracy_percentage": calculate_accuracy(len(students)),
            "cutoffs": serialize_cutoffs(cutoffs),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/allocation/{index_number}")
def get_student_allocation(
    index_number: str = Path(..., title="The student's index number"),
) -> dict[str, Any]:
    try:
        cutoffs, students = run_allocation_engine()
        target = next(
            (student for student in students if student["index"] == index_number), None
        )
        if not target:
            raise HTTPException(
                status_code=404,
                detail="Student not found or has incomplete results/preferences.",
            )

        return {
            "status": "success",
            "index_number": target["index"],
            "name": target["name"],
            "assigned_department": target["assigned_dept"],
            "average_gpa": float(target["average_gpa"]),
            "student_rank": target["student_rank"],
            "cutoffs": serialize_cutoffs(cutoffs),
            "total_students_processed": len(students),
            "accuracy_percentage": calculate_accuracy(len(students)),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
