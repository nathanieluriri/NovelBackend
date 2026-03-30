import asyncio

import pytest
from fastapi import HTTPException

from api.v1 import user as user_api
from schemas.user_schema import NewUserBase, OldUserBase, Provider


def test_google_signup_body_flow_is_rejected():
    payload = NewUserBase(
        provider=Provider.GOOGLE,
        email="user@example.com",
        googleAccessToken="legacy-token",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(user_api.register(payload))

    assert exc.value.status_code == 400
    assert "/api/v1/user/google/auth" in str(exc.value.detail)


def test_google_signin_body_flow_is_rejected():
    payload = OldUserBase(
        provider=Provider.GOOGLE,
        email="user@example.com",
        googleAccessToken="legacy-token",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(user_api.login(payload))

    assert exc.value.status_code == 400
    assert "/api/v1/user/google/auth" in str(exc.value.detail)
