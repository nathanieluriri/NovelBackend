import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from core.google_oauth_config import GoogleOAuthSettings, GoogleOAuthTarget
from schemas.google_oauth_schema import GoogleOAuthTargetEnum
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


def test_google_callback_prefers_state_alias_over_session(monkeypatch):
    """When the session is lost (or stale) the target alias must still be
    recovered from the OAuth ``state`` parameter — otherwise a ``target=dev``
    login would silently fall back to the default target."""

    async def fake_get_or_create_google_user(user_info):
        return {"_id": "a" * 24, "email": user_info["email"], "provider": "google"}

    async def fake_create_google_oauth_exchange(exchange_record):
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

    # Session is empty (simulating a dropped cookie), but the state param carries
    # the ``dev`` alias that the caller originally asked for.
    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(
                session={},
                query_params={"state": "dev:some-random-nonce"},
            )
        )
    )

    assert response.headers["location"] == (
        "https://sandbox-mei.vercel.app/portal/auth/success?code=one-time-code"
    )


def test_google_callback_state_alias_wins_over_session_alias(monkeypatch):
    async def fake_get_or_create_google_user(user_info):
        return {"_id": "a" * 24, "email": user_info["email"], "provider": "google"}

    async def fake_create_google_oauth_exchange(exchange_record):
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
            DummyRequest(
                session={"google_oauth_target_alias": "local"},
                query_params={"state": "dev:nonce"},
            )
        )
    )

    assert response.headers["location"].startswith(
        "https://sandbox-mei.vercel.app/portal/auth/success"
    )


def test_google_callback_error_uses_state_alias_when_session_lost(monkeypatch):
    """Even the error branch must honour the state-carried alias, otherwise
    every failed prod login would redirect to the default (local) frontend."""

    monkeypatch.setattr(google_oauth_service, "get_google_oauth_settings", _settings)

    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(
                session={},
                query_params={"error": "access_denied", "state": "dev:nonce"},
            )
        )
    )

    assert response.headers["location"] == (
        "https://sandbox-mei.vercel.app/portal/auth/error?error=access_denied"
    )


def test_decode_target_from_state_ignores_unknown_values():
    assert google_oauth_service._decode_target_from_state(None) is None
    assert google_oauth_service._decode_target_from_state("") is None
    assert google_oauth_service._decode_target_from_state("no-separator") is None
    assert google_oauth_service._decode_target_from_state(":only-nonce") is None
    # Legacy alias:nonce format still decodes
    assert google_oauth_service._decode_target_from_state("dev:nonce") == "dev"
    # URL-encoded alias in legacy format survives the round trip
    assert google_oauth_service._decode_target_from_state("my%20env:nonce") == "my env"


def test_encode_state_with_target_roundtrips():
    encoded = google_oauth_service._encode_state_with_target("prod")
    # New format is versioned base64-JSON — legacy shim still decodes it.
    assert encoded.startswith("v1.")
    assert google_oauth_service._decode_target_from_state(encoded) == "prod"


def test_encode_oauth_state_carries_redirect_path_through_roundtrip():
    encoded = google_oauth_service._encode_oauth_state("prod", "/settings/profile")
    assert encoded.startswith("v1.")
    decoded = google_oauth_service._decode_oauth_state(encoded)
    assert decoded["target"] == "prod"
    assert decoded["redirect_path"] == "/settings/profile"


def test_decode_oauth_state_drops_malicious_redirect_paths():
    # Even if someone hand-crafts a state blob with an absolute URL, the decoder
    # must refuse to surface it so it cannot end up in the frontend URL.
    import base64
    import json

    def _forge(payload):
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
        return "v1." + body

    for bad_path in [
        "https://evil.com/x",
        "//evil.com/x",
        "/\\evil.com",
        "http://evil",
        "javascript:alert(1)",
    ]:
        decoded = google_oauth_service._decode_oauth_state(_forge({"t": "prod", "r": bad_path}))
        assert "redirect_path" not in decoded, bad_path


def test_sanitize_redirect_path_accepts_valid_paths():
    sanitize = google_oauth_service._sanitize_redirect_path
    assert sanitize("/settings") == "/settings"
    assert sanitize("/books/123?tab=reviews") == "/books/123?tab=reviews"
    assert sanitize("/path#anchor") == "/path#anchor"
    # Leading/trailing whitespace is stripped but the path itself is untouched.
    assert sanitize("  /settings  ") == "/settings"


def test_sanitize_redirect_path_rejects_unsafe_inputs():
    sanitize = google_oauth_service._sanitize_redirect_path
    for bad in [
        None,
        "",
        "   ",
        "settings",                  # no leading slash
        "http://evil.com/path",      # absolute URL
        "//evil.com/path",           # protocol-relative
        "/\\evil.com",               # backslash trick
        "/%2fevil.com",              # encoded double-slash
        "/" + "a" * 600,             # too long
        123,                          # non-string
    ]:
        assert sanitize(bad) is None, bad


def test_google_callback_forwards_redirect_path_on_success(monkeypatch):
    async def fake_get_or_create_google_user(user_info):
        return {"_id": "a" * 24, "email": user_info["email"], "provider": "google"}

    async def fake_create_google_oauth_exchange(exchange_record):
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

    state_value = google_oauth_service._encode_oauth_state("dev", "/settings/profile")
    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(session={}, query_params={"state": state_value})
        )
    )

    location = response.headers["location"]
    assert location.startswith("https://sandbox-mei.vercel.app/portal/auth/success")
    assert "code=one-time-code" in location
    assert "redirect_path=%2Fsettings%2Fprofile" in location


def test_google_callback_forwards_redirect_path_on_error(monkeypatch):
    monkeypatch.setattr(google_oauth_service, "get_google_oauth_settings", _settings)

    state_value = google_oauth_service._encode_oauth_state("dev", "/settings")
    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(
                session={},
                query_params={"error": "access_denied", "state": state_value},
            )
        )
    )

    location = response.headers["location"]
    assert location.startswith("https://sandbox-mei.vercel.app/portal/auth/error")
    assert "error=access_denied" in location
    assert "redirect_path=%2Fsettings" in location


def test_google_callback_uses_session_redirect_path_when_state_missing(monkeypatch):
    async def fake_get_or_create_google_user(user_info):
        return {"_id": "a" * 24, "email": user_info["email"], "provider": "google"}

    async def fake_create_google_oauth_exchange(exchange_record):
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

    # No state param, but a legacy session still carries target + redirect_path.
    response = asyncio.run(
        google_oauth_service.handle_google_oauth_callback(
            DummyRequest(
                session={
                    "google_oauth_target_alias": "dev",
                    "google_oauth_redirect_path": "/library",
                },
                query_params={},
            )
        )
    )

    location = response.headers["location"]
    assert location.startswith("https://sandbox-mei.vercel.app/portal/auth/success")
    assert "redirect_path=%2Flibrary" in location


def test_target_enum_exposes_canonical_aliases():
    assert GoogleOAuthTargetEnum.LOCAL.value == "local"
    assert GoogleOAuthTargetEnum.DEV.value == "dev"
    assert GoogleOAuthTargetEnum.STAGING.value == "staging"
    assert GoogleOAuthTargetEnum.PROD.value == "prod"
    # Enum values round-trip cleanly through the state encoding.
    encoded = google_oauth_service._encode_oauth_state(GoogleOAuthTargetEnum.PROD.value)
    assert google_oauth_service._decode_oauth_state(encoded)["target"] == "prod"


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
