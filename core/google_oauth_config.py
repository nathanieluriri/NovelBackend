import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse


def _is_valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_valid_frontend_redirect_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    return bool(parsed.scheme) and bool(parsed.netloc or parsed.path)


@dataclass(frozen=True)
class GoogleOAuthTarget:
    alias: str
    success_url: str
    error_url: str


def _build_google_oauth_target(
    alias: str,
    *,
    success_url: str,
    error_url: str,
) -> GoogleOAuthTarget | None:
    normalized_success_url = success_url.strip()
    normalized_error_url = error_url.strip()
    if not normalized_success_url or not normalized_error_url:
        return None
    if not _is_valid_frontend_redirect_url(normalized_success_url):
        return None
    if not _is_valid_frontend_redirect_url(normalized_error_url):
        return None
    return GoogleOAuthTarget(
        alias=alias,
        success_url=normalized_success_url,
        error_url=normalized_error_url,
    )


def _parse_redirect_target_value(alias: str, value: object) -> GoogleOAuthTarget | None:
    if isinstance(value, str):
        return _build_google_oauth_target(alias, success_url=value, error_url=value)

    if not isinstance(value, dict):
        return None

    success_url = value.get("success")
    error_url = value.get("error")
    if not isinstance(success_url, str) or not isinstance(error_url, str):
        return None
    return _build_google_oauth_target(alias, success_url=success_url, error_url=error_url)


def _parse_redirect_targets(raw_value: str) -> dict[str, GoogleOAuthTarget]:
    if not raw_value.strip():
        return {}

    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}

    if not isinstance(decoded, dict):
        return {}

    targets: dict[str, GoogleOAuthTarget] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            continue
        alias = key.strip()
        if not alias:
            continue
        target = _parse_redirect_target_value(alias, value)
        if target is None:
            continue
        targets[alias] = target
    return targets


def _parse_exchange_ttl_seconds(raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return 120
    return max(parsed, 30)


def _parse_positive_int(raw_value: str | None, default: int) -> int:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None or not raw_value.strip():
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_same_site(raw_value: str | None, default: str) -> str:
    if raw_value is None or not raw_value.strip():
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"lax", "strict", "none"}:
        return normalized
    return default


def _extract_origin(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _parse_origin_list(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return []

    parsed_values: list[str]
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        decoded = None

    if isinstance(decoded, list):
        parsed_values = [value for value in decoded if isinstance(value, str)]
    else:
        parsed_values = [value.strip() for value in raw_value.split(",")]

    origins: list[str] = []
    seen: set[str] = set()
    for value in parsed_values:
        origin = _extract_origin(value)
        if origin is None or origin in seen:
            continue
        origins.append(origin)
        seen.add(origin)
    return origins


def _derive_cors_allowed_origins(redirect_targets: dict[str, "GoogleOAuthTarget"]) -> list[str]:
    origins: list[str] = []
    seen: set[str] = set()
    for target in redirect_targets.values():
        for url in (target.success_url, target.error_url):
            origin = _extract_origin(url)
            if origin is None or origin in seen:
                continue
            origins.append(origin)
            seen.add(origin)
    return origins


@dataclass(frozen=True)
class GoogleOAuthSettings:
    client_id: str
    client_secret: str
    callback_url: str
    redirect_targets: dict[str, GoogleOAuthTarget]
    default_target: str
    exchange_ttl_seconds: int
    session_secret_key: str
    session_cookie_name: str = "mei_session"
    session_cookie_same_site: str = "lax"
    session_cookie_https_only: bool = False
    session_cookie_domain: str | None = None
    session_cookie_max_age: int = 900
    cors_allowed_origins: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "GoogleOAuthSettings":
        redirect_targets = _parse_redirect_targets(os.getenv("GOOGLE_OAUTH_REDIRECT_TARGETS", ""))
        callback_url = os.getenv("GOOGLE_OAUTH_CALLBACK_URL", "").strip()
        default_target = os.getenv("GOOGLE_OAUTH_DEFAULT_TARGET", "").strip()
        if not default_target and redirect_targets:
            default_target = next(iter(redirect_targets))
        callback_is_https = urlparse(callback_url).scheme == "https"
        cors_allowed_origins = _parse_origin_list(os.getenv("CORS_ALLOWED_ORIGINS", ""))
        if not cors_allowed_origins:
            cors_allowed_origins = _derive_cors_allowed_origins(redirect_targets)

        return cls(
            client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
            callback_url=callback_url,
            redirect_targets=redirect_targets,
            default_target=default_target,
            exchange_ttl_seconds=_parse_exchange_ttl_seconds(
                os.getenv("GOOGLE_OAUTH_EXCHANGE_TTL_SECONDS", "120")
            ),
            session_secret_key=os.getenv("SESSION_SECRET_KEY", "some-random-string"),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "mei_session").strip() or "mei_session",
            session_cookie_same_site=_parse_same_site(
                os.getenv("SESSION_COOKIE_SAME_SITE"),
                default="none" if callback_is_https else "lax",
            ),
            session_cookie_https_only=_parse_bool(
                os.getenv("SESSION_COOKIE_HTTPS_ONLY"),
                default=callback_is_https,
            ),
            session_cookie_domain=os.getenv("SESSION_COOKIE_DOMAIN", "").strip() or None,
            session_cookie_max_age=_parse_positive_int(
                os.getenv("SESSION_COOKIE_MAX_AGE"),
                default=max(900, _parse_exchange_ttl_seconds(os.getenv("GOOGLE_OAUTH_EXCHANGE_TTL_SECONDS", "120"))),
            ),
            cors_allowed_origins=cors_allowed_origins,
        )

    def resolve_target(self, requested_alias: str | None = None) -> GoogleOAuthTarget:
        if not self.redirect_targets:
            raise ValueError("GOOGLE_OAUTH_REDIRECT_TARGETS is not configured")

        alias = (requested_alias or self.default_target).strip()
        if not alias:
            raise ValueError("GOOGLE_OAUTH_DEFAULT_TARGET is not configured")

        target = self.redirect_targets.get(alias)
        if target is None:
            raise ValueError(f"Unknown Google OAuth redirect target: {alias}")

        return target

    def validate_runtime(self) -> None:
        missing_settings: list[str] = []
        if not self.client_id:
            missing_settings.append("GOOGLE_CLIENT_ID")
        if not self.client_secret:
            missing_settings.append("GOOGLE_CLIENT_SECRET")
        if not self.callback_url:
            missing_settings.append("GOOGLE_OAUTH_CALLBACK_URL")
        elif not _is_valid_http_url(self.callback_url):
            missing_settings.append("GOOGLE_OAUTH_CALLBACK_URL (must be a valid http/https URL)")

        if not self.redirect_targets:
            missing_settings.append("GOOGLE_OAUTH_REDIRECT_TARGETS")
        elif self.default_target and self.default_target not in self.redirect_targets:
            missing_settings.append("GOOGLE_OAUTH_DEFAULT_TARGET (must match a redirect target alias)")
        if self.session_cookie_same_site == "none" and not self.session_cookie_https_only:
            missing_settings.append("SESSION_COOKIE_HTTPS_ONLY (must be true when SESSION_COOKIE_SAME_SITE=none)")

        if missing_settings:
            raise ValueError(", ".join(missing_settings))


@lru_cache(maxsize=1)
def get_google_oauth_settings() -> GoogleOAuthSettings:
    return GoogleOAuthSettings.from_env()
