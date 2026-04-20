import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from core.google_oauth_config import GoogleOAuthSettings, GoogleOAuthTarget, get_google_oauth_settings
from repositories.google_oauth_repo import create_google_oauth_exchange, consume_google_oauth_exchange
from repositories.user_repo import add_auth_provider_to_user, create_user, get_user_by_email, get_user_by_userId
from schemas.google_oauth_schema import GoogleOAuthExchangeRecordCreate, GoogleOAuthExchangeRequest
from schemas.user_schema import NewUserCreate, OldUserOut, Provider
from services.user_service import build_authenticated_user_output


_GOOGLE_OAUTH_TARGET_SESSION_KEY = "google_oauth_target_alias"
_GOOGLE_OAUTH_REDIRECT_PATH_SESSION_KEY = "google_oauth_redirect_path"
_GOOGLE_OAUTH_STATE_SEPARATOR = ":"
_GOOGLE_OAUTH_STATE_PREFIX = "v1."  # versioned base64-JSON states
_GOOGLE_OAUTH_MAX_REDIRECT_PATH_LENGTH = 512


def _sanitize_redirect_path(raw_path: str | None) -> str | None:
    """Normalize and validate a caller-supplied post-login ``redirect_path``.

    Only relative paths (starting with a single ``/``) are accepted so that the
    feature cannot be abused as an open redirect. The path may include a query
    string and fragment, but no scheme, host, or userinfo.
    """
    if not isinstance(raw_path, str):
        return None
    path = raw_path.strip()
    if not path:
        return None
    if len(path) > _GOOGLE_OAUTH_MAX_REDIRECT_PATH_LENGTH:
        return None
    # Must be rooted at the frontend origin.
    if not path.startswith("/"):
        return None
    # Reject protocol-relative ("//evil.com/x") and backslash variants that some
    # browsers interpret as absolute URLs.
    if path.startswith("//") or path.startswith("/\\") or path.startswith("/%2F") or path.startswith("/%2f"):
        return None
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return None
    return path


def _encode_oauth_state(target_alias: str, redirect_path: str | None = None) -> str:
    """Encode flow metadata into the OAuth ``state`` parameter.

    The state survives the Google round-trip as a query param, so using it as
    the source of truth makes the flow resilient to session-cookie loss.
    """
    payload: dict[str, Any] = {
        "t": target_alias,
        "n": secrets.token_urlsafe(24),
    }
    if redirect_path:
        payload["r"] = redirect_path
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return _GOOGLE_OAUTH_STATE_PREFIX + encoded


def _decode_oauth_state(state_value: str | None) -> dict[str, str]:
    """Decode ``state`` produced by :func:`_encode_oauth_state`.

    Returns a dict with optional keys ``target`` and ``redirect_path``. The
    legacy ``alias:nonce`` format is accepted too so that in-flight redirects
    created by older builds of the service keep working.
    """
    if not isinstance(state_value, str) or not state_value:
        return {}

    # New format: "v1." + base64url(JSON)
    if state_value.startswith(_GOOGLE_OAUTH_STATE_PREFIX):
        body = state_value[len(_GOOGLE_OAUTH_STATE_PREFIX):]
        try:
            padding = "=" * (-len(body) % 4)
            raw = base64.urlsafe_b64decode(body + padding).decode("utf-8")
            payload = json.loads(raw)
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        result: dict[str, str] = {}
        target = payload.get("t")
        if isinstance(target, str) and target.strip():
            result["target"] = target.strip()
        redirect_path = _sanitize_redirect_path(payload.get("r") if isinstance(payload.get("r"), str) else None)
        if redirect_path:
            result["redirect_path"] = redirect_path
        return result

    # Legacy format: "<url-encoded-alias>:<nonce>"
    head, sep, _rest = state_value.partition(_GOOGLE_OAUTH_STATE_SEPARATOR)
    if not sep or not head:
        return {}
    try:
        alias = unquote(head).strip()
    except Exception:
        return {}
    return {"target": alias} if alias else {}


# Deprecated shims kept so external call sites (and tests) can still reach the
# underlying primitives. Prefer :func:`_encode_oauth_state` /
# :func:`_decode_oauth_state`.
def _encode_state_with_target(target_alias: str) -> str:
    return _encode_oauth_state(target_alias)


def _decode_target_from_state(state_value: str | None) -> str | None:
    return _decode_oauth_state(state_value).get("target")


if TYPE_CHECKING:
    from authlib.integrations.starlette_client import OAuth


def _missing_authlib_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Google OAuth dependency is missing: install authlib",
    )


@lru_cache(maxsize=1)
def get_google_oauth_client() -> Any:
    try:
        from authlib.integrations.starlette_client import OAuth
    except ModuleNotFoundError as err:
        raise _missing_authlib_exception() from err

    settings = get_google_oauth_settings()
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def _append_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(params)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _normalize_error_code(value: str | None) -> str:
    if not value:
        return "google_oauth_failed"
    return value.strip().lower().replace(" ", "_")


def _hash_exchange_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_exchange_code() -> str:
    return secrets.token_urlsafe(32)


def _ensure_google_oauth_configured(settings: GoogleOAuthSettings) -> None:
    try:
        settings.validate_runtime()
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth is not configured correctly: {err}",
        ) from err


def _resolve_frontend_target(
    settings: GoogleOAuthSettings,
    target_alias: str | None,
    *,
    invalid_alias_status: int = status.HTTP_400_BAD_REQUEST,
) -> GoogleOAuthTarget:
    try:
        return settings.resolve_target(target_alias)
    except ValueError as err:
        message = str(err)
        if message.startswith("Unknown Google OAuth redirect target:"):
            raise HTTPException(status_code=invalid_alias_status, detail=message) from err
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth is not configured correctly: {message}",
        ) from err


def _build_success_redirect_url(
    frontend_target: GoogleOAuthTarget,
    code: str,
    redirect_path: str | None = None,
) -> str:
    params: dict[str, str] = {"code": code}
    if redirect_path:
        params["redirect_path"] = redirect_path
    return _append_query_params(frontend_target.success_url, params)


def _build_error_redirect_url(
    frontend_target: GoogleOAuthTarget,
    error_code: str,
    redirect_path: str | None = None,
) -> str:
    params: dict[str, str] = {"error": _normalize_error_code(error_code)}
    if redirect_path:
        params["redirect_path"] = redirect_path
    return _append_query_params(frontend_target.error_url, params)


def _extract_profile_value(user_info: dict[str, Any], key: str) -> str | None:
    value = user_info.get(key)
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return None


def _build_profile_updates(existing_user: dict[str, Any], user_info: dict[str, Any]) -> dict[str, str]:
    updates: dict[str, str] = {}
    first_name = _extract_profile_value(user_info, "given_name")
    last_name = _extract_profile_value(user_info, "family_name")
    avatar = _extract_profile_value(user_info, "picture")

    if first_name and not existing_user.get("firstName"):
        updates["firstName"] = first_name
    if last_name and not existing_user.get("lastName"):
        updates["lastName"] = last_name
    if avatar and not existing_user.get("avatar"):
        updates["avatar"] = avatar
    return updates


async def _get_or_create_google_user(user_info: dict[str, Any]) -> dict[str, Any]:
    email = _extract_profile_value(user_info, "email")
    if email is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account email is missing")

    if user_info.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified",
        )

    existing_user = await get_user_by_email(email)
    if existing_user is not None:
        profile_updates = _build_profile_updates(existing_user, user_info)
        updated_user = await add_auth_provider_to_user(
            user_id=str(existing_user["_id"]),
            provider=Provider.GOOGLE.value,
            profile_updates=profile_updates,
        )
        if updated_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated_user

    new_user = NewUserCreate(
        provider=Provider.GOOGLE,
        email=email,
        password=None,
        firstName=_extract_profile_value(user_info, "given_name"),
        lastName=_extract_profile_value(user_info, "family_name"),
        avatar=_extract_profile_value(user_info, "picture"),
        authProviders=[Provider.GOOGLE.value],
    )
    await new_user.model_async_validate()
    return await create_user(new_user)


async def start_google_oauth(
    request: Request,
    target_alias: str | None,
    redirect_path: str | None = None,
) -> RedirectResponse:
    settings = get_google_oauth_settings()
    _ensure_google_oauth_configured(settings)
    target = _resolve_frontend_target(settings, target_alias)
    sanitized_redirect_path = _sanitize_redirect_path(redirect_path)

    # Keep the alias + redirect_path in session as a secondary source; the
    # primary source is the OAuth ``state`` parameter below, which round-trips
    # through Google and is not affected by session cookie loss.
    request.session[_GOOGLE_OAUTH_TARGET_SESSION_KEY] = target.alias
    if sanitized_redirect_path:
        request.session[_GOOGLE_OAUTH_REDIRECT_PATH_SESSION_KEY] = sanitized_redirect_path
    else:
        request.session.pop(_GOOGLE_OAUTH_REDIRECT_PATH_SESSION_KEY, None)

    oauth = get_google_oauth_client()
    state_value = _encode_oauth_state(target.alias, sanitized_redirect_path)
    return await oauth.google.authorize_redirect(
        request,
        settings.callback_url,
        state=state_value,
    )


_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def _is_state_mismatch_error(err: Exception) -> bool:
    """Heuristically detect authlib's state/CSRF mismatch error.

    We avoid a hard import of `authlib.integrations.base_client.errors` because
    that module path has moved across authlib versions; matching on the class
    name plus a small set of error strings keeps the recovery path working
    whether the installed version raises `MismatchingStateError`,
    `MismatchingState`, or a plain `AuthlibBaseError` with `error="mismatching_state"`.
    """
    class_name = err.__class__.__name__
    if class_name in {"MismatchingStateError", "MismatchingState", "CSRFError"}:
        return True
    marker = (getattr(err, "error", None) or "").lower()
    return marker in {"mismatching_state", "csrf", "missing_state"}


def _decode_id_token_payload(id_token: str) -> dict[str, Any]:
    """Decode the JWT payload without signature verification.

    The id_token was just fetched over TLS from Google's token endpoint using
    our client secret, so the transport authenticates the source. Signature
    verification is skipped here because, when we take this code path, the
    session has been lost and we no longer have the original OIDC ``nonce`` to
    compare against.
    """
    parts = id_token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


async def _manual_google_code_exchange(
    settings: GoogleOAuthSettings, code: str
) -> dict[str, Any] | None:
    """Exchange an authorization code with Google, bypassing authlib's state check.

    Returns the userinfo dict on success, `None` on any failure.
    """
    try:
        from authlib.integrations.httpx_client import AsyncOAuth2Client
    except ModuleNotFoundError:
        return None

    try:
        async with AsyncOAuth2Client(
            client_id=settings.client_id,
            client_secret=settings.client_secret,
        ) as oauth_client:
            token = await oauth_client.fetch_token(
                _GOOGLE_TOKEN_ENDPOINT,
                code=code,
                grant_type="authorization_code",
                redirect_uri=settings.callback_url,
            )
    except Exception:
        return None

    id_token = token.get("id_token") if isinstance(token, dict) else None
    if isinstance(id_token, str):
        userinfo = _decode_id_token_payload(id_token)
        if userinfo:
            return userinfo

    access_token = token.get("access_token") if isinstance(token, dict) else None
    if not isinstance(access_token, str):
        return None
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                _GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _resolve_callback_flow_metadata(
    request: Request,
    settings: GoogleOAuthSettings,
) -> tuple[str | None, str | None]:
    """Resolve ``(target_alias, redirect_path)`` for a callback request.

    Prefer values embedded in the OAuth ``state`` query parameter because it
    survives the Google round-trip even when the session cookie is not sent
    back (cross-site SameSite=Lax quirks, reverse-proxy cookie stripping, HTTPS
    downgrade). Fall back to the session for backwards compatibility.
    """
    state_payload = _decode_oauth_state(request.query_params.get("state"))
    state_alias = state_payload.get("target")
    state_redirect_path = state_payload.get("redirect_path")

    session_alias = request.session.pop(_GOOGLE_OAUTH_TARGET_SESSION_KEY, None)
    session_redirect_path = request.session.pop(_GOOGLE_OAUTH_REDIRECT_PATH_SESSION_KEY, None)

    if state_alias and state_alias in settings.redirect_targets:
        resolved_alias: str | None = state_alias
    else:
        resolved_alias = session_alias

    resolved_redirect_path = state_redirect_path or _sanitize_redirect_path(session_redirect_path)
    return resolved_alias, resolved_redirect_path


async def handle_google_oauth_callback(request: Request) -> RedirectResponse:
    settings = get_google_oauth_settings()
    _ensure_google_oauth_configured(settings)

    stored_target_alias, redirect_path = _resolve_callback_flow_metadata(request, settings)
    frontend_target = _resolve_frontend_target(
        settings,
        stored_target_alias,
        invalid_alias_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    callback_error = request.query_params.get("error")
    if callback_error:
        redirect_url = _build_error_redirect_url(frontend_target, callback_error, redirect_path)
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    oauth = get_google_oauth_client()
    user_info: dict[str, Any] | None = None
    token: dict[str, Any] | None = None
    try:
        token = await oauth.google.authorize_access_token(request)
    except HTTPException:
        raise
    except Exception as err:
        # When the session cookie fails to round-trip (cross-site SameSite,
        # reverse-proxy cookie stripping, HTTPS downgrade), authlib raises
        # MismatchingStateError before it even tries to exchange the code.
        # The design of our own `state` payload explicitly makes it the
        # fallback source of truth, so we finish the flow manually instead of
        # bouncing the user to the frontend's error URL.
        state_payload = _decode_oauth_state(request.query_params.get("state"))
        authorization_code = request.query_params.get("code")
        if (
            _is_state_mismatch_error(err)
            and state_payload
            and isinstance(authorization_code, str)
            and authorization_code
        ):
            user_info = await _manual_google_code_exchange(settings, authorization_code)
        if user_info is None:
            redirect_url = _build_error_redirect_url(
                frontend_target,
                getattr(err, "error", None) or str(err),
                redirect_path,
            )
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    if user_info is None and isinstance(token, dict):
        maybe_userinfo = token.get("userinfo")
        if isinstance(maybe_userinfo, dict):
            user_info = maybe_userinfo
        else:
            try:
                parsed = await oauth.google.parse_id_token(request, token)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                user_info = parsed
    if not isinstance(user_info, dict):
        redirect_url = _build_error_redirect_url(frontend_target, "missing_google_userinfo", redirect_path)
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    try:
        user = await _get_or_create_google_user(user_info)
    except HTTPException as err:
        redirect_url = _build_error_redirect_url(frontend_target, str(err.detail), redirect_path)
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    code = _generate_exchange_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.exchange_ttl_seconds)
    await create_google_oauth_exchange(
        GoogleOAuthExchangeRecordCreate(
            codeHash=_hash_exchange_code(code),
            userId=str(user["_id"]),
            targetAlias=frontend_target.alias,
            expiresAt=expires_at,
        )
    )

    redirect_url = _build_success_redirect_url(frontend_target, code, redirect_path)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


async def exchange_google_oauth_code(exchange_request: GoogleOAuthExchangeRequest) -> OldUserOut:
    exchange_record = await consume_google_oauth_exchange(_hash_exchange_code(exchange_request.code))
    if exchange_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google OAuth code is invalid, expired, or already used",
        )

    user = await get_user_by_userId(exchange_record.userId)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return await build_authenticated_user_output(user)
