from core.google_oauth_config import get_google_oauth_settings


def test_google_oauth_settings_use_default_target(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_TARGETS",
        (
            '{"dev":{"success":"https://sandbox-mei.vercel.app/portal/auth/success",'
            '"error":"https://sandbox-mei.vercel.app/portal/auth/error"},'
            '"local":{"success":"http://localhost:3001/portal/auth/success",'
            '"error":"http://localhost:3001/portal/auth/error"}}'
        ),
    )
    monkeypatch.setenv("GOOGLE_OAUTH_DEFAULT_TARGET", "dev")
    get_google_oauth_settings.cache_clear()

    try:
        settings = get_google_oauth_settings()
        target = settings.resolve_target()
    finally:
        get_google_oauth_settings.cache_clear()

    assert target.alias == "dev"
    assert target.success_url == "https://sandbox-mei.vercel.app/portal/auth/success"
    assert target.error_url == "https://sandbox-mei.vercel.app/portal/auth/error"


def test_google_oauth_settings_pick_first_target_when_default_missing(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_TARGETS",
        '{"local":{"success":"http://localhost:3001/portal/auth/success","error":"http://localhost:3001/portal/auth/error"}}',
    )
    monkeypatch.delenv("GOOGLE_OAUTH_DEFAULT_TARGET", raising=False)
    get_google_oauth_settings.cache_clear()

    try:
        settings = get_google_oauth_settings()
        target = settings.resolve_target()
    finally:
        get_google_oauth_settings.cache_clear()

    assert target.alias == "local"
    assert target.success_url == "http://localhost:3001/portal/auth/success"
    assert target.error_url == "http://localhost:3001/portal/auth/error"


def test_google_oauth_settings_accept_mobile_deep_links(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_TARGETS",
        '{"mobile":{"success":"mei://portal/auth/success","error":"mei://portal/auth/error"}}',
    )
    monkeypatch.setenv("GOOGLE_OAUTH_DEFAULT_TARGET", "mobile")
    get_google_oauth_settings.cache_clear()

    try:
        settings = get_google_oauth_settings()
        target = settings.resolve_target()
    finally:
        get_google_oauth_settings.cache_clear()

    assert target.alias == "mobile"
    assert target.success_url == "mei://portal/auth/success"
    assert target.error_url == "mei://portal/auth/error"
