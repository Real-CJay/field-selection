import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
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


def test_magic_link_responses_do_not_enumerate_registry_or_expose_email(monkeypatch):
    database = object()
    outcomes = []
    sent_payloads = []
    reservation_ids = iter((1, 2, 3))
    monkeypatch.setenv("FRONTEND_AUTH_CALLBACK_URL", "https://example.test/auth/callback")
    monkeypatch.setattr(api_server, "verify_turnstile", lambda *_: None)
    monkeypatch.setattr(api_server, "get_supabase", lambda: database)
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: next(reservation_ids))
    monkeypatch.setattr(api_server, "set_auth_request_outcome", lambda _database, request_id, outcome: outcomes.append((request_id, outcome)))
    monkeypatch.setattr(
        api_server,
        "get_supabase_auth",
        lambda: SimpleNamespace(auth=SimpleNamespace(
            sign_in_with_otp=lambda payload: sent_payloads.append(payload)
        )),
    )

    responses = []
    for student in (
        None,
        {"index_number": "250544U", "name": "Student", "email": None},
        {"index_number": "250544U", "name": "Student", "email": "private@example.test"},
    ):
        monkeypatch.setattr(api_server, "find_student_auth_record_by_index", lambda *_args, value=student: value)
        responses.append(api_server.send_student_magic_link(
            api_server.StudentMagicLinkInput(index_number="250544u", turnstile_token="turnstile"),
            request_from(),
        ))

    assert responses[0] == responses[1] == responses[2]
    assert "private@example.test" not in json.dumps(responses)
    assert sent_payloads == [{
        "email": "private@example.test",
        "options": {
            "email_redirect_to": "https://example.test/auth/callback",
            "should_create_user": True,
        },
    }]
    assert outcomes == [(3, "sent")]


def test_password_login_is_generic_for_unknown_indexes_and_records_failure(monkeypatch):
    monkeypatch.setattr(api_server, "verify_turnstile", lambda *_: None)
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 1)
    monkeypatch.setattr(api_server, "find_student_auth_record_by_index", lambda *_: None)

    with pytest.raises(HTTPException) as error:
        api_server.sign_in_student_with_password(
            api_server.StudentPasswordInput(
                index_number="250544U", password="incorrect-password", turnstile_token="turnstile"
            ),
            request_from(),
        )

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid index number or personal password."


def test_password_login_returns_only_supabase_session_tokens(monkeypatch):
    monkeypatch.setattr(api_server, "verify_turnstile", lambda *_: None)
    monkeypatch.setattr(api_server, "get_supabase", lambda: object())
    monkeypatch.setattr(api_server, "reserve_auth_request", lambda *_: 1)
    monkeypatch.setattr(
        api_server,
        "find_student_auth_record_by_index",
        lambda *_: {"index_number": "250544U", "email": "private@example.test"},
    )
    outcomes = []
    monkeypatch.setattr(api_server, "set_auth_request_outcome", lambda _database, request_id, outcome: outcomes.append((request_id, outcome)))
    session = SimpleNamespace(
        access_token="access", refresh_token="refresh", expires_at=1234, token_type="bearer"
    )
    monkeypatch.setattr(
        api_server,
        "get_supabase_auth",
        lambda: SimpleNamespace(auth=SimpleNamespace(
            sign_in_with_password=lambda _payload: SimpleNamespace(session=session)
        )),
    )

    response = api_server.sign_in_student_with_password(
        api_server.StudentPasswordInput(
            index_number="250544U", password="personal-password", turnstile_token="turnstile"
        ),
        request_from(),
    )
    assert response == {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_at": 1234,
        "token_type": "bearer",
    }
    assert "private@example.test" not in json.dumps(response)
    assert outcomes == [(1, "success")]


def test_request_hashes_are_keyed_and_do_not_contain_source_values(monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_HMAC_KEY", "a-long-random-test-key")
    first = api_server.auth_request_hash("index:250544U")
    second = api_server.auth_request_hash("index:250544U")
    assert first == second
    assert len(first) == 64
    assert "250544U" not in first


def test_magic_link_cooldown_is_enforced(monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_HMAC_KEY", "a-long-random-test-key")

    class RateLimitedDatabase:
        def rpc(self, _name, _parameters):
            return self

        def execute(self):
            raise RuntimeError("AUTH_RATE_LIMIT")

    with pytest.raises(HTTPException) as error:
        api_server.reserve_auth_request(
            RateLimitedDatabase(), "250544U", "203.0.113.10", "magic_link"
        )
    assert error.value.status_code == 429


def test_authenticated_identity_is_bound_to_the_verified_student(monkeypatch):
    user = SimpleNamespace(id="auth-user-id", email="private@example.test")
    database = SimpleNamespace(auth=SimpleNamespace(
        get_user=lambda _token: SimpleNamespace(user=user)
    ))
    monkeypatch.setattr(api_server, "get_supabase", lambda: database)
    monkeypatch.setattr(
        api_server,
        "find_student_auth_record_by_email",
        lambda *_: {
            "index_number": "250544U",
            "name": "Student",
            "email": "private@example.test",
            "auth_user_id": "auth-user-id",
        },
    )
    monkeypatch.setenv("MAINTENANCE_MODE", "true")
    monkeypatch.setenv("MAINTENANCE_PREVIEW_INDEXES", "250314P,250544U")

    identity = api_server.require_student(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")
    )
    assert identity == {
        "index_number": "250544U",
        "name": "Student",
        "auth_user_id": "auth-user-id",
    }
    assert "email" not in identity
