import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from core.google_oauth_config import GoogleOAuthSettings, GoogleOAuthTarget, get_google_oauth_settings
from repositories.google_oauth_repo import create_google_oauth_exchange, consume_google_oauth_exchange
from repositories.user_repo import add_auth_provider_to_user, create_user, get_user_by_email, get_user_by_userId
from schemas.google_oauth_schema import GoogleOAuthExchangeRecordCreate, GoogleOAuthExchangeRequest
from schemas.user_schema import NewUserCreate, OldUserOut, Provider
from services.user_service import build_authenticated_user_output


_GOOGLE_OAUTH_TARGET_SESSION_KEY = "google_oauth_target_alias"

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


def _build_success_redirect_url(frontend_target: GoogleOAuthTarget, code: str) -> str:
    return _append_query_params(frontend_target.success_url, {"code": code})


def _build_error_redirect_url(frontend_target: GoogleOAuthTarget, error_code: str) -> str:
    return _append_query_params(
        frontend_target.error_url,
        {"error": _normalize_error_code(error_code)},
    )


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


async def start_google_oauth(request: Request, target_alias: str | None) -> RedirectResponse:
    settings = get_google_oauth_settings()
    _ensure_google_oauth_configured(settings)
    target = _resolve_frontend_target(settings, target_alias)
    request.session[_GOOGLE_OAUTH_TARGET_SESSION_KEY] = target.alias
    oauth = get_google_oauth_client()
    return await oauth.google.authorize_redirect(request, settings.callback_url)


async def handle_google_oauth_callback(request: Request) -> RedirectResponse:
    settings = get_google_oauth_settings()
    _ensure_google_oauth_configured(settings)

    stored_target_alias = request.session.pop(_GOOGLE_OAUTH_TARGET_SESSION_KEY, None)
    frontend_target = _resolve_frontend_target(
        settings,
        stored_target_alias,
        invalid_alias_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    callback_error = request.query_params.get("error")
    if callback_error:
        redirect_url = _build_error_redirect_url(frontend_target, callback_error)
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    oauth = get_google_oauth_client()
    try:
        token = await oauth.google.authorize_access_token(request)
    except HTTPException:
        raise
    except Exception as err:
        redirect_url = _build_error_redirect_url(
            frontend_target,
            getattr(err, "error", None) or str(err),
        )
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    user_info = token.get("userinfo")
    if not isinstance(user_info, dict):
        try:
            user_info = await oauth.google.parse_id_token(request, token)
        except Exception:
            user_info = None
    if not isinstance(user_info, dict):
        redirect_url = _build_error_redirect_url(frontend_target, "missing_google_userinfo")
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    try:
        user = await _get_or_create_google_user(user_info)
    except HTTPException as err:
        redirect_url = _build_error_redirect_url(frontend_target, str(err.detail))
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

    redirect_url = _build_success_redirect_url(frontend_target, code)
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
