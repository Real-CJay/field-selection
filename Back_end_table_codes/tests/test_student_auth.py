import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from starlette.requests import Request

import api_server


def request_from(ip_address: str = "203.0.113.10") -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [],
        "client": (ip_address, 12345),
    })


def configure_student_login(monkeypatch, student):
    monkeypatch.setenv("STUDENT_READONLY_PASSWORD", "student123")
    monkeypatch.setenv(
        "STUDENT_READ_TOKEN_SECRET", "read-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setenv(
        "STUDENT_EDIT_TOKEN_SECRET", "edit-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setenv(
        "STUDENT_CREDENTIAL_PEPPER", "pepper-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 1)
    monkeypatch.setattr(
        api_server, "find_student_auth_record_by_index", lambda *_: student
    )
    monkeypatch.setattr(api_server, "find_student_credential", lambda *_: None)
    outcomes = []
    monkeypatch.setattr(
        api_server,
        "set_auth_request_outcome",
        lambda _database, request_id, outcome: outcomes.append((request_id, outcome)),
    )
    return outcomes


def test_shared_password_login_returns_only_read_only_identity(monkeypatch):
    outcomes = configure_student_login(
        monkeypatch, {"index_number": "250745L", "name": "MM Bassam"}
    )

    response = api_server.sign_in_student(
        api_server.StudentLoginInput(index_number="250745l", password="student123"),
        request_from(),
    )

    assert response["access_mode"] == "read-only"
    assert response["index_number"] == "250745L"
    assert response["name"] == "MM Bassam"
    assert response["read_token"].startswith("read.")
    assert "email" not in response
    assert outcomes == [(1, "success")]


@pytest.mark.parametrize(
    ("student", "password"),
    [
        (None, "student123"),
        ({"index_number": "250544U", "name": "Student"}, "personal-password"),
        ({"index_number": "250544U", "name": "Student"}, "wrong-password"),
    ],
)
def test_unknown_indexes_and_every_other_password_are_rejected_generically(
    monkeypatch, student, password
):
    configure_student_login(monkeypatch, student)

    with pytest.raises(HTTPException) as error:
        api_server.sign_in_student(
            api_server.StudentLoginInput(index_number="250544U", password=password),
            request_from(),
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid index number or password."


def test_request_hashes_are_keyed_and_do_not_contain_source_values(monkeypatch):
    monkeypatch.setenv(
        "AUTH_RATE_LIMIT_HMAC_KEY", "a-long-random-test-key-at-least-32-characters"
    )
    first = api_server.auth_request_hash("index:250544U")
    second = api_server.auth_request_hash("index:250544U")
    assert first == second
    assert len(first) == 64
    assert "250544U" not in first


def test_login_rate_limit_is_enforced(monkeypatch):
    monkeypatch.setenv(
        "AUTH_RATE_LIMIT_HMAC_KEY", "a-long-random-test-key-at-least-32-characters"
    )

    class RateLimitedDatabase:
        def rpc(self, _name, _parameters):
            return self

        def execute(self):
            raise RuntimeError("AUTH_RATE_LIMIT")

    with pytest.raises(HTTPException) as error:
        api_server.reserve_auth_request(
            RateLimitedDatabase(), "250544U", "203.0.113.10", "login"
        )
    assert error.value.status_code == 429


def test_read_token_is_short_lived_signed_and_bound_to_one_index(monkeypatch):
    monkeypatch.setenv(
        "STUDENT_READ_TOKEN_SECRET", "read-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(
        api_server,
        "find_student_auth_record_by_index",
        lambda *_: {"index_number": "250544U", "name": "Student"},
    )
    token = api_server.issue_signed_token("read", "250544U", 60)
    payload = api_server.verify_signed_token(token, "read")
    assert payload["sub"] == "250544U"
    assert payload["exp"] - payload["iat"] == 60

    identity = api_server.require_student_access(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    assert identity == {
        "index_number": "250544U",
        "name": "Student",
        "access_mode": "read-only",
    }

    with pytest.raises(HTTPException) as error:
        api_server.get_student_allocation("250314P", identity)
    assert error.value.status_code == 403


def test_admin_login_no_longer_requires_turnstile(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "CJay")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv(
        "ADMIN_TOKEN_SECRET", "admin-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 1)
    monkeypatch.setattr(api_server, "set_auth_request_outcome", lambda *_: None)

    response = api_server.admin_login(
        api_server.AdminLoginInput(username="cjay", password="admin-password"),
        request_from(),
    )
    assert response["username"] == "CJay"
    assert response["admin_token"].startswith("admin.")


def test_magic_link_is_removed_and_student_writes_default_to_disabled(monkeypatch):
    client = TestClient(api_server.app)
    assert client.post("/api/student/auth/magic-link", json={}).status_code == 404

    correction = client.post(
        "/api/correction-requests",
        json={"module": "cse", "requested_grade": "A"},
    )
    assert correction.status_code == 503
    assert correction.json()["detail"].startswith("Student editing")


def test_personal_password_login_returns_editable_versioned_token(monkeypatch):
    configure_student_login(
        monkeypatch, {"index_number": "250544U", "name": "Student"}
    )
    password_hash = api_server.hash_credential("my personal password")
    monkeypatch.setattr(
        api_server,
        "find_student_credential",
        lambda *_: {
            "index_number": "250544U",
            "recovery_code_hash": "unused",
            "personal_password_hash": password_hash,
            "password_version": 4,
            "recovery_version": 1,
        },
    )

    response = api_server.sign_in_student(
        api_server.StudentLoginInput(
            index_number="250544u", password="my personal password"
        ),
        request_from(),
    )

    assert response["access_mode"] == "editable"
    assert response["edit_token"].startswith("edit.")
    payload = api_server.verify_signed_token(response["edit_token"], "edit")
    assert payload["sub"] == "250544U"
    assert payload["ver"] == 4


def test_recovery_codes_accept_grouping_and_reject_non_digits():
    assert api_server.normalize_recovery_code("0123-4567-8901-2345") == "0123456789012345"
    assert api_server.normalize_recovery_code("0123 4567 8901 2345") == "0123456789012345"
    assert api_server.normalize_recovery_code("0123-4567-8901-234X") is None
    assert api_server.normalize_recovery_code("123456") is None


def test_password_rules_reject_shared_short_and_mismatched_passwords():
    client = TestClient(api_server.app)
    base = {"password_setup_token": "x" * 32}
    cases = [
        ({**base, "password": "short", "password_confirmation": "short"}, 422),
        ({**base, "password": "student123", "password_confirmation": "student123"}, 422),
        ({**base, "password": "allowed", "password_confirmation": "different"}, 422),
    ]
    for payload, expected_status in cases:
        assert client.post("/api/student/auth/password", json=payload).status_code == expected_status


def test_password_setup_consumes_challenge_and_returns_editable_token(monkeypatch):
    monkeypatch.setenv("STUDENT_READONLY_PASSWORD", "student123")
    monkeypatch.setenv(
        "STUDENT_EDIT_TOKEN_SECRET", "edit-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setenv(
        "STUDENT_CREDENTIAL_PEPPER", "pepper-secret-that-is-at-least-32-characters"
    )

    class RpcResult:
        data = [{"index_number": "250544U", "password_version": 2}]

    class Database:
        def rpc(self, name, params):
            assert name == "consume_student_password_challenge"
            assert "p_password_hash" in params
            return self

        def execute(self):
            return RpcResult()

    monkeypatch.setattr(api_server, "get_supabase", lambda: Database())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 8)
    monkeypatch.setattr(api_server, "set_auth_request_outcome", lambda *_: None)
    monkeypatch.setattr(
        api_server,
        "find_student_auth_record_by_index",
        lambda *_: {"index_number": "250544U", "name": "Student"},
    )
    response = api_server.create_or_reset_student_password(
        api_server.StudentPasswordSetupInput(
            password_setup_token="x" * 32,
            password="allowed password",
            password_confirmation="allowed password",
        ),
        request_from(),
    )
    assert response["access_mode"] == "editable"
    assert api_server.verify_signed_token(response["edit_token"], "edit")["ver"] == 2


def test_password_version_change_invalidates_existing_edit_token(monkeypatch):
    monkeypatch.setenv(
        "STUDENT_EDIT_TOKEN_SECRET", "edit-secret-that-is-at-least-32-characters"
    )
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(
        api_server,
        "find_student_auth_record_by_index",
        lambda *_: {"index_number": "250544U", "name": "Student"},
    )
    version = {"value": 1}
    monkeypatch.setattr(
        api_server,
        "find_student_credential",
        lambda *_: {"password_version": version["value"]},
    )
    token = api_server.issue_signed_token("edit", "250544U", 60, {"ver": 1})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert api_server.authenticate_student_token(credentials)["access_mode"] == "editable"
    version["value"] = 2
    with pytest.raises(HTTPException) as error:
        api_server.authenticate_student_token(credentials)
    assert error.value.status_code == 401


def test_read_only_token_cannot_unlock_student_writes(monkeypatch):
    monkeypatch.setenv("STUDENT_WRITES_ENABLED", "true")
    monkeypatch.setenv(
        "STUDENT_READ_TOKEN_SECRET", "read-secret-that-is-at-least-32-characters"
    )
    token = api_server.issue_signed_token("read", "250544U", 60)
    with pytest.raises(HTTPException) as error:
        api_server.require_editable_student(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
    assert error.value.status_code == 403


def test_preference_write_uses_token_identity_and_validates_unique_ranks(monkeypatch):
    captured = {}

    class Query:
        data = []

        def upsert(self, payload, **_kwargs):
            captured.update(payload)
            return self

        def execute(self):
            return self

    class Database:
        def table(self, name):
            assert name == "student_preferences"
            return Query()

    monkeypatch.setattr(api_server, "get_supabase", lambda: Database())
    valid = api_server.StudentPreferencesUpdateInput(**{
        department: rank
        for rank, department in enumerate(api_server.BASE_QUOTAS, start=1)
    })
    api_server.update_student_preferences(
        valid,
        {"index_number": "250544U", "name": "Student", "access_mode": "editable"},
    )
    assert captured["index_number"] == "250544U"
    assert sorted(captured[department] for department in api_server.BASE_QUOTAS) == list(range(1, 11))

    duplicate = api_server.StudentPreferencesUpdateInput(**{
        department: 1 for department in api_server.BASE_QUOTAS
    })
    with pytest.raises(HTTPException) as error:
        api_server.update_student_preferences(
            duplicate,
            {"index_number": "250544U", "name": "Student", "access_mode": "editable"},
        )
    assert error.value.status_code == 422


def test_recovery_verification_stores_only_hashes(monkeypatch):
    monkeypatch.setenv(
        "STUDENT_CREDENTIAL_PEPPER", "pepper-secret-that-is-at-least-32-characters"
    )
    recovery_hash = api_server.hash_credential("0123456789012345")
    inserted = {}

    class Query:
        def insert(self, payload):
            inserted.update(payload)
            return self

        def execute(self):
            return type("Result", (), {"data": [inserted]})()

    class Database:
        def table(self, name):
            assert name == "student_password_challenges"
            return Query()

    monkeypatch.setattr(api_server, "get_supabase", lambda: Database())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 1)
    monkeypatch.setattr(api_server, "set_auth_request_outcome", lambda *_: None)
    monkeypatch.setattr(
        api_server,
        "find_student_auth_record_by_index",
        lambda *_: {"index_number": "250544U", "name": "Student"},
    )
    monkeypatch.setattr(
        api_server,
        "find_student_credential",
        lambda *_: {
            "recovery_code_hash": recovery_hash,
            "recovery_version": 3,
        },
    )
    response = api_server.verify_student_recovery_code(
        api_server.StudentRecoveryVerifyInput(
            index_number="250544U", recovery_code="0123-4567-8901-2345"
        ),
        request_from(),
    )
    assert response["expires_in"] == 600
    assert "0123456789012345" not in str(inserted)
    assert inserted["token_hash"] != response["password_setup_token"]


def test_sensitive_read_routes_reject_missing_bearer_tokens():
    client = TestClient(api_server.app)
    for path in (
        "/api/student/record",
        "/api/cutoffs",
        "/api/gpa-lookup?gpa=3.50",
        "/api/allocation/250544U",
        "/api/departments/computer/gpas",
        "/api/admin/departments",
        "/api/admin/students",
        "/api/admin/correction-requests",
    ):
        response = client.get(path)
        assert response.status_code == 401, path
