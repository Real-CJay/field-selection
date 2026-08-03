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
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 1)
    monkeypatch.setattr(
        api_server, "find_student_auth_record_by_index", lambda *_: student
    )
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


def test_removed_auth_routes_are_not_available_and_student_writes_are_disabled():
    client = TestClient(api_server.app)
    for path in (
        "/api/student/auth/magic-link",
        "/api/student/auth/password",
        "/api/student/auth/me",
    ):
        assert client.post(path, json={}).status_code == 404

    correction = client.post(
        "/api/correction-requests",
        json={"module": "cse", "requested_grade": "A"},
    )
    assert correction.status_code == 503
    assert correction.json()["detail"].startswith("Grade correction requests")


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
