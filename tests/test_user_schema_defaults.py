from schemas.user_schema import ReadingHistory, UserOut


def test_user_out_stopped_reading_uses_instance_default():
    user = UserOut.model_validate({"_id": "a" * 24, "email": "user@example.com"})

    assert isinstance(user.stopped_reading, ReadingHistory)
    dumped = user.model_dump()
    assert isinstance(dumped["stopped_reading"], dict)
    assert dumped["stopped_reading"]["chapterId"] is not None

