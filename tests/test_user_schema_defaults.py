from schemas.user_schema import UserOut


def test_user_out_stopped_reading_defaults_to_none():
    user = UserOut.model_validate({"_id": "a" * 24, "email": "user@example.com"})

    assert user.stopped_reading is None
    dumped = user.model_dump()
    assert dumped["stopped_reading"] is None


def test_user_out_auth_providers_default_from_legacy_provider():
    user = UserOut.model_validate(
        {
            "_id": "b" * 24,
            "email": "user@example.com",
            "provider": "credentials",
        }
    )

    assert user.authProviders == ["credentials"]
