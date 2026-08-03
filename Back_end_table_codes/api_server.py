from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import hashlib
import hmac
from itertools import combinations
import json
import logging
from math import comb
import os
import re
import secrets
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request as UrlRequest, urlopen

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, Field
from supabase import Client, create_client

load_dotenv()

api_docs_enabled = os.environ.get("ENABLE_API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="Field Selection Allocation API",
    docs_url="/docs" if api_docs_enabled else None,
    redoc_url="/redoc" if api_docs_enabled else None,
    openapi_url="/openapi.json" if api_docs_enabled else None,
)
logger = logging.getLogger("field_selection_api")

frontend_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_URL", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    return response

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
student_bearer = HTTPBearer(auto_error=False)
admin_bearer = HTTPBearer(auto_error=False)
GENERIC_MAGIC_LINK_MESSAGE = (
    "If an eligible registered email address exists, a confirmation link has been sent. "
    "Please check your inbox and spam folder."
)
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


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
    module: str
    requested_grade: str


class StudentMagicLinkInput(BaseModel):
    index_number: str = Field(min_length=1, max_length=32)
    turnstile_token: str = Field(min_length=1, max_length=2048)


class StudentPasswordInput(BaseModel):
    index_number: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=256)
    turnstile_token: str = Field(min_length=1, max_length=2048)


class StudentLoginInput(StudentPasswordInput):
    pass


class AdminLoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    turnstile_token: str = Field(min_length=1, max_length=2048)


class CorrectionDecisionInput(BaseModel):
    decision: str


class AdminGradeUpdateInput(BaseModel):
    cse: str | None = None
    maths: str | None = None
    electrical: str | None = None
    fluids: str | None = None
    mechanics: str | None = None
    material: str | None = None
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


def get_supabase_auth() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be configured."
        )
    # Auth clients hold session state, so create one per request instead of sharing it.
    return create_client(url, key)


def normalize_index_number(value: str) -> str:
    return value.strip().upper()


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def signed_token_secret(token_type: str) -> str:
    variable = (
        "ADMIN_TOKEN_SECRET" if token_type == "admin" else "STUDENT_READ_TOKEN_SECRET"
    )
    secret = os.environ.get(variable)
    if not secret or len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Secure session authentication is not configured.",
        )
    return secret


def issue_signed_token(token_type: str, subject: str, lifetime_seconds: int) -> str:
    current_time = int(time.time())
    payload = {
        "typ": token_type,
        "sub": subject,
        "iat": current_time,
        "exp": current_time + lifetime_seconds,
        "nonce": secrets.token_urlsafe(12),
    }
    encoded_payload = _urlsafe_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        signed_token_secret(token_type).encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{token_type}.{encoded_payload}.{_urlsafe_encode(signature)}"


def verify_signed_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        token_type, encoded_payload, encoded_signature = token.split(".", 2)
        if token_type != expected_type:
            raise ValueError("unexpected token type")
        expected_signature = hmac.new(
            signed_token_secret(expected_type).encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not secrets.compare_digest(
            _urlsafe_decode(encoded_signature), expected_signature
        ):
            raise ValueError("invalid signature")
        payload = json.loads(_urlsafe_decode(encoded_payload).decode("utf-8"))
        current_time = int(time.time())
        issued_at = int(payload.get("iat", 0))
        expires_at = int(payload.get("exp", 0))
        if (
            payload.get("typ") != expected_type
            or issued_at <= 0
            or issued_at > current_time + 60
            or expires_at <= current_time
            or expires_at - issued_at > 60 * 60
        ):
            raise ValueError("expired token")
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise ValueError("invalid subject")
        return payload
    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        UnicodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        ) from None


def student_auth_is_allowed(index_number: str) -> bool:
    maintenance_enabled = os.environ.get("MAINTENANCE_MODE", "true").lower() != "false"
    if not maintenance_enabled:
        return True
    configured = os.environ.get(
        "MAINTENANCE_PREVIEW_INDEXES", "250314P,250544U"
    )
    allowed = {
        normalize_index_number(value)
        for value in configured.split(",")
        if value.strip()
    }
    return normalize_index_number(index_number) in allowed


def request_ip(request: Request) -> str:
    if os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true":
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def verify_turnstile(
    token: str, remote_ip: str, expected_action: str = "student-auth"
) -> None:
    secret = os.environ.get("TURNSTILE_SECRET_KEY")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Student verification is not configured.",
        )
    if not token.strip():
        raise HTTPException(status_code=422, detail="Complete the security check.")

    body = urlencode({
        "secret": secret,
        "response": token,
        "remoteip": remote_ip,
    }).encode("utf-8")
    verification_request = UrlRequest(
        TURNSTILE_VERIFY_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(verification_request, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to complete the security check. Please try again.",
        ) from error

    if not result.get("success"):
        raise HTTPException(status_code=422, detail="Complete the security check again.")
    action = result.get("action")
    if action != expected_action:
        raise HTTPException(status_code=422, detail="Complete the security check again.")
    configured_hostnames = {
        value.strip().lower()
        for value in os.environ.get("TURNSTILE_ALLOWED_HOSTNAMES", "").split(",")
        if value.strip()
    }
    if not configured_hostnames:
        configured_hostnames = {
            parsed.hostname.lower()
            for origin in frontend_origins
            if (parsed := urlparse(origin)).hostname
        }
    hostname = str(result.get("hostname") or "").lower()
    if configured_hostnames and hostname not in configured_hostnames:
        raise HTTPException(status_code=422, detail="Complete the security check again.")


def auth_request_hash(value: str) -> str:
    key = os.environ.get("AUTH_RATE_LIMIT_HMAC_KEY")
    if not key or len(key) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Student authentication limits are not configured.",
        )
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def reserve_auth_request(
    database: Client, index_number: str, remote_ip: str, request_type: str
) -> int:
    index_hash = auth_request_hash(f"index:{normalize_index_number(index_number)}")
    ip_hash = auth_request_hash(f"ip:{remote_ip}")
    try:
        response = database.rpc("reserve_student_auth_request", {
            "p_index_hash": index_hash,
            "p_ip_hash": ip_hash,
            "p_request_type": request_type,
        }).execute()
    except Exception as error:
        if "AUTH_RATE_LIMIT" in str(error):
            detail = (
                "Please wait before requesting another confirmation email."
                if request_type == "magic_link"
                else "Too many unsuccessful attempts. Please wait and try again."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            ) from error
        raise
    request_id = response.data[0] if isinstance(response.data, list) else response.data
    if isinstance(request_id, dict):
        request_id = next(iter(request_id.values()), None)
    if not isinstance(request_id, int):
        raise RuntimeError("Authentication request reservation failed.")
    return request_id


def set_auth_request_outcome(database: Client, request_id: int, outcome: str) -> None:
    database.table("student_auth_requests").update({"outcome": outcome}).eq(
        "id", request_id
    ).execute()


def find_student_auth_record_by_index(
    database: Client, index_number: str
) -> dict[str, Any] | None:
    response = (
        database.table("students")
        .select("index_number,name,email,auth_user_id")
        .eq("index_number", normalize_index_number(index_number))
        .maybe_single()
        .execute()
    )
    return response.data


def find_student_auth_record_by_email(
    database: Client, email: str
) -> dict[str, Any] | None:
    response = (
        database.table("students")
        .select("index_number,name,email,auth_user_id")
        .ilike("email", email)
        .execute()
    )
    matches = [
        row for row in response.data
        if isinstance(row.get("email"), str)
        and row["email"].strip().lower() == email.strip().lower()
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def bind_authenticated_student(email: str, user_id: str) -> dict[str, Any]:
    database = get_supabase()
    student = find_student_auth_record_by_email(database, email)
    if not student:
        raise HTTPException(status_code=403, detail="This account is not linked to a student.")
    if not student_auth_is_allowed(student["index_number"]):
        raise HTTPException(status_code=403, detail="The site is currently under maintenance.")
    current_owner = student.get("auth_user_id")
    if current_owner is None:
        database.table("students").update({"auth_user_id": user_id}).eq(
            "index_number", student["index_number"]
        ).is_("auth_user_id", "null").execute()
        student = find_student_auth_record_by_email(database, email)
        current_owner = student.get("auth_user_id") if student else None
    if str(current_owner) != user_id:
        raise HTTPException(status_code=409, detail="This student account is already linked.")
    return {
        "index_number": student["index_number"],
        "name": student["name"],
        "auth_user_id": user_id,
        "access_mode": "editable",
    }


def student_from_supabase_token(access_token: str) -> dict[str, Any]:
    try:
        user_response = get_supabase().auth.get_user(access_token)
        user = user_response.user if user_response else None
        email = getattr(user, "email", None)
        user_id = str(getattr(user, "id", ""))
        if not user or not isinstance(email, str) or not user_id:
            raise HTTPException(status_code=401, detail="Student authentication is required.")
        return bind_authenticated_student(email, user_id)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=401, detail="Student authentication is required.") from error


def require_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(student_bearer),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Student authentication is required.")
    return student_from_supabase_token(credentials.credentials)


def require_student_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(student_bearer),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Student authentication is required.")
    token = credentials.credentials
    if token.startswith("read."):
        payload = verify_signed_token(token, "read")
        index_number = normalize_index_number(payload["sub"])
        student = find_student_auth_record_by_index(get_supabase(), index_number)
        if not student:
            raise HTTPException(status_code=401, detail="Student authentication is required.")
        return {
            "index_number": student["index_number"],
            "name": student["name"],
            "access_mode": "read-only",
        }
    return student_from_supabase_token(token)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_bearer),
) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Administrator authentication is required.")
    return str(verify_signed_token(credentials.credentials, "admin")["sub"])


def log_admin_action(
    database: Client,
    admin_username: str,
    action: str,
    target: str,
    details: dict[str, Any] | None = None,
) -> None:
    database.table("admin_action_audit").insert({
        "admin_username": admin_username,
        "action": action,
        "target": target,
        "details": details or {},
    }).execute()


def internal_server_exception(error: Exception) -> HTTPException:
    logger.error("Unhandled API error type=%s", type(error).__name__)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to complete the request. Please try again.",
    )


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
    states: list[AllocationState],
    overflow_gpa: Decimal | None,
    quotas: dict[str, int] | None = None,
) -> dict[str, dict[str, Any]]:
    quotas = quotas or BASE_QUOTAS
    result: dict[str, dict[str, Any]] = {}
    for department in states[0].cutoffs_dict():
        selected_counts = [
            sum(assigned == department for _, assigned in state.assignments)
            for state in states
        ]
        seat_fill = {
            "selected_min": min(selected_counts, default=0),
            "selected_max": max(selected_counts, default=0),
            "quota": quotas[department],
        }
        closed_states = [
            state for state in states if state.remaining_dict()[department] == 0
        ]
        values = [state.cutoffs_dict()[department] for state in closed_states]
        numeric = sorted({value for value in values if value is not None})
        open_possible = len(closed_states) != len(states)
        if not numeric:
            result[department] = {
                "status": "open", "incomplete": overflow_gpa is not None, **seat_fill
            }
        elif len(numeric) == 1 and not open_possible:
            result[department] = {
                "status": "fixed",
                "value": float(numeric[0]),
                "incomplete": overflow_gpa is not None, **seat_fill,
            }
        else:
            result[department] = {
                "status": "range",
                "min": float(numeric[0]),
                "max": float(numeric[-1]),
                "open_possible": open_possible,
                "incomplete": overflow_gpa is not None, **seat_fill,
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
            f"With the submissions currently available, the estimate is no lower than "
            f"{guaranteed} or a higher-ranked preference."
        )
    else:
        explanation = (
            "Your placement is on an unresolved allocation border. Current submissions and "
            "subject marks are not sufficient to give a lower-bound estimate."
        )
    return {
        "allocation_status": "border",
        "assigned_department": None,
        "possible_departments": departments,
        "border_departments": border_departments,
        "guaranteed_department": guaranteed,
        "allocation_explanation": explanation,
    }


def anonymous_min_group_size() -> int:
    try:
        return max(
            2, min(20, int(os.environ.get("ANONYMOUS_LOOKUP_MIN_GROUP_SIZE", "3")))
        )
    except ValueError:
        return 3


def aggregate_department_gpas(
    department: str,
    states: list[AllocationState],
    students: list[dict[str, Any]],
    overflow_gpa: Decimal | None,
    minimum_group_size: int | None = None,
) -> list[dict[str, Any]]:
    minimum_group_size = minimum_group_size or anonymous_min_group_size()
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
        if max(counts, default=0) < minimum_group_size:
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
    cutoffs = aggregate_cutoffs(states, overflow_gpa, quotas)
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

    minimum_group_size = anonymous_min_group_size()
    details_suppressed = 0 < len(matching) < minimum_group_size
    return {
        "gpa": float(target_gpa),
        "count": len(matching),
        "total_students_processed": len(students),
        "details_suppressed": details_suppressed,
        "minimum_group_size": minimum_group_size,
        "allocation_groups": [] if details_suppressed else allocation_groups,
        "tiebreak_groups": [] if details_suppressed else tiebreak_groups,
    }


def calculate_cohort_coverage(total_students: int) -> float:
    return round(min(100, total_students / TOTAL_COHORT * 100), 1)


@app.post("/api/student/auth/magic-link", status_code=status.HTTP_202_ACCEPTED)
def send_student_magic_link(
    submitted: StudentMagicLinkInput,
    request: Request,
) -> dict[str, str]:
    remote_ip = request_ip(request)
    verify_turnstile(submitted.turnstile_token, remote_ip)
    index_number = normalize_index_number(submitted.index_number)
    generic_response = {"status": "accepted", "message": GENERIC_MAGIC_LINK_MESSAGE}

    if not student_auth_is_allowed(index_number):
        return generic_response

    try:
        database = get_supabase()
        request_id = reserve_auth_request(database, index_number, remote_ip, "magic_link")
        student = find_student_auth_record_by_index(database, index_number)
        email = student.get("email") if student else None
        if not isinstance(email, str) or not email.strip():
            return generic_response

        redirect_url = os.environ.get("FRONTEND_AUTH_CALLBACK_URL")
        if not redirect_url:
            raise RuntimeError("FRONTEND_AUTH_CALLBACK_URL must be configured.")
        get_supabase_auth().auth.sign_in_with_otp({
            "email": email.strip(),
            "options": {
                "email_redirect_to": redirect_url,
                "should_create_user": True,
            },
        })
        set_auth_request_outcome(database, request_id, "sent")
        return generic_response
    except HTTPException:
        raise
    except Exception as error:
        # Do not let SMTP/configuration failures reveal whether an index has an email.
        logger.warning(
            "A student magic-link request could not be completed; error_type=%s",
            type(error).__name__,
        )
        return generic_response


@app.post("/api/student/auth/password")
def sign_in_student_with_password(
    submitted: StudentPasswordInput,
    request: Request,
) -> dict[str, Any]:
    remote_ip = request_ip(request)
    verify_turnstile(submitted.turnstile_token, remote_ip)
    index_number = normalize_index_number(submitted.index_number)
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid index number or personal password.",
    )
    if not student_auth_is_allowed(index_number):
        raise invalid_credentials

    try:
        database = get_supabase()
        request_id = reserve_auth_request(database, index_number, remote_ip, "password")
        student = find_student_auth_record_by_index(database, index_number)
        email = student.get("email") if student else None
        if not isinstance(email, str) or not email.strip():
            raise invalid_credentials

        try:
            auth_response = get_supabase_auth().auth.sign_in_with_password({
                "email": email.strip(),
                "password": submitted.password,
            })
        except Exception:
            raise invalid_credentials
        session = auth_response.session
        if not session:
            raise invalid_credentials
        set_auth_request_outcome(database, request_id, "success")
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
            "token_type": session.token_type,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to sign in. Please try again.",
        ) from error


@app.post("/api/student/auth/login")
def sign_in_student(
    submitted: StudentLoginInput,
    request: Request,
) -> dict[str, Any]:
    remote_ip = request_ip(request)
    verify_turnstile(submitted.turnstile_token, remote_ip)
    index_number = normalize_index_number(submitted.index_number)
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid index number or password.",
    )
    try:
        database = get_supabase()
        request_id = reserve_auth_request(database, index_number, remote_ip, "login")
        student = find_student_auth_record_by_index(database, index_number)
        if not student:
            raise invalid_credentials

        shared_password = os.environ.get("STUDENT_READONLY_PASSWORD")
        if shared_password and secrets.compare_digest(submitted.password, shared_password):
            set_auth_request_outcome(database, request_id, "success")
            return {
                "access_mode": "read-only",
                "read_token": issue_signed_token("read", index_number, 30 * 60),
                "index_number": student["index_number"],
                "name": student["name"],
            }

        if not student_auth_is_allowed(index_number):
            raise invalid_credentials

        email = student.get("email")
        if not isinstance(email, str) or not email.strip():
            raise invalid_credentials
        try:
            auth_response = get_supabase_auth().auth.sign_in_with_password({
                "email": email.strip(),
                "password": submitted.password,
            })
        except Exception:
            raise invalid_credentials
        auth_session = auth_response.session
        if not auth_session:
            raise invalid_credentials
        identity = student_from_supabase_token(auth_session.access_token)
        if identity["index_number"] != index_number:
            raise invalid_credentials
        set_auth_request_outcome(database, request_id, "success")
        return {
            "access_mode": "editable",
            "access_token": auth_session.access_token,
            "refresh_token": auth_session.refresh_token,
            "expires_at": auth_session.expires_at,
            "token_type": auth_session.token_type,
            "index_number": identity["index_number"],
            "name": identity["name"],
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Student login failed; error_type=%s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to sign in. Please try again.",
        ) from error


@app.get("/api/student/auth/me")
def get_authenticated_student(
    student: dict[str, Any] = Depends(require_student_access),
) -> dict[str, str]:
    return {
        "index_number": student["index_number"],
        "name": student["name"],
    }


@app.get("/api/student/record")
def get_student_record(
    student: dict[str, Any] = Depends(require_student_access),
) -> dict[str, Any]:
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
            .eq("index_number", student["index_number"])
            .maybe_single()
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Student record was not found.")
        raw_results = response.data.get("student_results")
        raw_preferences = response.data.get("student_preferences")
        results = raw_results[0] if isinstance(raw_results, list) and raw_results else raw_results
        preferences = (
            raw_preferences[0]
            if isinstance(raw_preferences, list) and raw_preferences
            else raw_preferences
        )
        return {
            "index_number": response.data["index_number"],
            "name": response.data["name"],
            "results": results,
            "preferences": preferences,
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Unable to load student record; error_type=%s", type(error).__name__)
        raise HTTPException(status_code=500, detail="Unable to load the student record.") from error


@app.get("/api/cutoffs")
def get_estimated_cutoffs(
    _: dict[str, Any] = Depends(require_student_access),
) -> dict[str, Any]:
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            "total_students_processed": len(students),
            "coverage_percentage": calculate_cohort_coverage(len(students)),
            "cutoffs": aggregate_cutoffs(states, overflow_gpa),
            "allocation_incomplete": overflow_gpa is not None,
        }
    except Exception as error:
        raise internal_server_exception(error) from error


@app.get("/api/gpa-lookup")
def get_gpa_lookup(
    gpa: str,
    _: dict[str, Any] = Depends(require_student_access),
) -> dict[str, Any]:
    target_gpa = parse_lookup_gpa(gpa)
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            **aggregate_gpa_lookup(target_gpa, states, students, overflow_gpa),
        }
    except Exception as error:
        raise internal_server_exception(error) from error


@app.get("/api/allocation/{index_number}")
def get_student_allocation(
    index_number: str = Path(..., title="The student's index number"),
    student_access: dict[str, Any] = Depends(require_student_access),
) -> dict[str, Any]:
    requested_index = normalize_index_number(index_number)
    if requested_index != student_access["index_number"]:
        raise HTTPException(status_code=403, detail="You can only view your own allocation.")
    try:
        states, students, overflow_gpa = run_allocation_engine()
        target = next(
            (student for student in students if student["index"] == requested_index), None
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
            "coverage_percentage": calculate_cohort_coverage(len(students)),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise internal_server_exception(error) from error


@app.get("/api/departments/{department}/gpas")
def get_department_gpas(
    department: str,
    _: dict[str, Any] = Depends(require_student_access),
) -> dict[str, Any]:
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
            "minimum_group_size": anonymous_min_group_size(),
            "incomplete": overflow_gpa is not None,
        }
    except Exception as error:
        raise internal_server_exception(error) from error


@app.post("/api/admin/login")
def admin_login(submitted: AdminLoginInput, request: Request) -> dict[str, str]:
    remote_ip = request_ip(request)
    verify_turnstile(submitted.turnstile_token, remote_ip, "admin-auth")
    expected_username = os.environ.get("ADMIN_USERNAME")
    expected_password = os.environ.get("ADMIN_PASSWORD")
    try:
        database = get_supabase()
        request_id = reserve_auth_request(
            database, f"admin:{submitted.username.lower()}", remote_ip, "admin_login"
        )
        valid = bool(expected_username and expected_password)
        if valid:
            valid = secrets.compare_digest(
                submitted.username.casefold(), expected_username.casefold()
            ) and secrets.compare_digest(submitted.password, expected_password)
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid administrator credentials.")
        set_auth_request_outcome(database, request_id, "success")
        return {
            "status": "success",
            "username": expected_username,
            "admin_token": issue_signed_token("admin", expected_username, 60 * 60),
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Administrator login failed; error_type=%s", type(error).__name__)
        raise HTTPException(
            status_code=503, detail="Administrator login is temporarily unavailable."
        ) from error


@app.get("/api/admin/departments")
def list_admin_departments(_: str = Depends(require_admin)) -> dict[str, Any]:
    try:
        states, students, overflow_gpa = run_allocation_engine()
        return {
            "status": "success",
            "departments": aggregate_admin_departments(states, students, overflow_gpa),
        }
    except Exception as error:
        raise internal_server_exception(error) from error


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
        raise internal_server_exception(error) from error


@app.patch("/api/admin/students/{index_number}/grades")
def update_admin_student_grades(
    update: AdminGradeUpdateInput,
    index_number: str,
    admin_username: str = Depends(require_admin),
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

        log_admin_action(
            database,
            admin_username,
            "student_grades_updated",
            normalize_index_number(index_number),
            {"modules": sorted(submitted)},
        )
        return {"status": "success", "average_gpa": numeric_updates["average_gpa"]}
    except HTTPException:
        raise
    except Exception as error:
        raise internal_server_exception(error) from error


@app.post("/api/correction-requests", status_code=status.HTTP_201_CREATED)
def create_correction_request(
    submitted: CorrectionRequestInput,
    student: dict[str, Any] = Depends(require_student),
) -> dict[str, Any]:
    module = submitted.module.strip().lower()
    grade = submitted.requested_grade.strip().upper()
    index_number = student["index_number"]
    if module not in CORRECTABLE_MODULES or grade not in GRADE_VALUES:
        raise HTTPException(status_code=422, detail="Invalid module or requested grade.")

    try:
        database = get_supabase()
        result = (
            database.table("student_results")
            .select(f"index_number,{module}")
            .eq("index_number", index_number)
            .maybe_single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Student results were not found.")

        existing = (
            database.table("grade_correction_requests")
            .select("id")
            .eq("index_number", index_number)
            .eq("module", module)
            .eq("status", "pending")
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="A pending request already exists for this module.")

        payload = {
            "index_number": index_number,
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
        raise internal_server_exception(error) from error


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
        raise internal_server_exception(error) from error


@app.post("/api/admin/correction-requests/{request_id}/revert")
def revert_correction_request(
    request_id: int = Path(..., ge=1),
    admin_username: str = Depends(require_admin),
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
        log_admin_action(
            database,
            admin_username,
            "correction_reverted",
            str(request_id),
            {"index_number": correction["index_number"], "module": module},
        )
        return {"status": "success", "average_gpa": average_gpa}
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        raise internal_server_exception(error) from error


@app.patch("/api/admin/correction-requests/{request_id}")
def review_correction_request(
    decision: CorrectionDecisionInput,
    request_id: int = Path(..., ge=1),
    admin_username: str = Depends(require_admin),
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
        log_admin_action(
            database,
            admin_username,
            "correction_reviewed",
            str(request_id),
            {
                "index_number": correction["index_number"],
                "module": correction["module"],
                "decision": decision.decision,
            },
        )
        return {"status": "success", "decision": decision.decision}
    except HTTPException:
        raise
    except Exception as error:
        raise internal_server_exception(error) from error
