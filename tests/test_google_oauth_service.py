import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from core.google_oauth_config import GoogleOAuthSettings, GoogleOAuthTarget
from services import google_oauth_service


@dataclass
class DummyRequest:
    session: dict
    query_params: dict


class DummyGoogleClient:
    async def authorize_access_token(self, request):
        return {
            "userinfo": {
                "email": "user@example.com",
                "email_verified": True,
                "given_name": "Jane",
                "family_name": "Doe",
                "picture": "https://example.com/avatar.jpg",
            }
        }


class DummyOAuth:
    google = DummyGoogleClient()


def _settings() -> GoogleOAuthSettings:
    return GoogleOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        callback_url="https://api.example.com/api/v1/user/google/callback",
        redirect_targets={
            "dev": GoogleOAuthTarget(
                alias="dev",
                success_url="https://sandbox-mei.vercel.app/portal/auth/success",
                error_url="https://sandbox-mei.vercel.app/portal/auth/error",
            ),
            "local": GoogleOAuthTarget(
                alias="local",
                success_url="http://localhost:3001/portal/auth/success",
                error_url="http://localhost:3001/portal/auth/error",
            ),
        },
        default_target="dev",
        exchange_ttl_seconds=120,
        session_secret_key="session-secret",
    )


def test_google_callback_redirects_with_one_time_code(monkeypatch):
    created_exchange = {}

    async def fake_get_or_create_google_user(user_info):
        return {"_id": "a" * 24, "email": user_info["email"], "provider": "google"}

    async def fake_create_google_oauth_exchange(exchange_record):
        created_exchange["record"] = exchange_record
        return exchange_record

    monkeypatch.setattr(google_oauth_service, "get_google_oauth_settings", _settings)
    monkeypatch.setattr(google_oauth_service, "get_google_oauth_client", lambda: DummyOAuth())
    monkeypatch.setattr(google_oauth_service, "_get_or_create_google_user", fake_get_or_create_google_user)
    monkeypatch.setattr(
        google_oauth_service,
        "create_google_oauth_exchange",
        fake_create_google_oauth_exchange,
    )
    monkeypatch.setattr(google_oauth_service, "_generate_exchange_code", lambda: "one-time-code")

    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(session={"google_oauth_target_alias": "dev"}, query_params={})
        )
    )

    location = response.headers["location"]
    assert location == "https://sandbox-mei.vercel.app/portal/auth/success?code=one-time-code"
    assert "accessToken" not in location
    assert "refreshToken" not in location
    assert created_exchange["record"].targetAlias == "dev"


def test_google_callback_redirects_errors_to_error_url(monkeypatch):
    monkeypatch.setattr(google_oauth_service, "get_google_oauth_settings", _settings)

    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(
                session={"google_oauth_target_alias": "local"},
                query_params={"error": "access_denied"},
            )
        )
    )

    assert response.headers["location"] == "http://localhost:3001/portal/auth/error?error=access_denied"


def test_exchange_google_oauth_code_rejects_invalid_code(monkeypatch):
    async def fake_consume_google_oauth_exchange(code_hash):
        return None

    monkeypatch.setattr(
        google_oauth_service,
        "consume_google_oauth_exchange",
        fake_consume_google_oauth_exchange,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            google_oauth_service.exchange_google_oauth_code(
                google_oauth_service.GoogleOAuthExchangeRequest(code="stale-code")
            )
        )

    assert exc.value.status_code == 401


def test_get_or_create_google_user_links_existing_credentials_user(monkeypatch):
    existing_user = {
        "_id": "b" * 24,
        "email": "user@example.com",
        "provider": "credentials",
        "firstName": None,
        "lastName": None,
        "avatar": None,
    }
    captured = {}

    async def fake_get_user_by_email(email):
        return existing_user

    async def fake_add_auth_provider_to_user(user_id, provider, profile_updates=None):
        captured["user_id"] = user_id
        captured["provider"] = provider
        captured["profile_updates"] = profile_updates
        updated_user = dict(existing_user)
        updated_user["authProviders"] = ["credentials", "google"]
        updated_user.update(profile_updates or {})
        return updated_user

    monkeypatch.setattr(google_oauth_service, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(
        google_oauth_service,
        "add_auth_provider_to_user",
        fake_add_auth_provider_to_user,
    )

    user = asyncio.run(
        google_oauth_service._get_or_create_google_user(
            {
                "email": "user@example.com",
                "email_verified": True,
                "given_name": "Jane",
                "family_name": "Doe",
                "picture": "https://example.com/avatar.jpg",
            }
        )
    )

    assert user["authProviders"] == ["credentials", "google"]
    assert captured["provider"] == "google"
    assert captured["profile_updates"] == {
        "firstName": "Jane",
        "lastName": "Doe",
        "avatar": "https://example.com/avatar.jpg",
    }
