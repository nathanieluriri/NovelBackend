import asyncio

import pytest
from fastapi import HTTPException

from schemas.bookmark_schema import (
    BookMarkCreate,
    BookMarkCreateRequest,
    BookMarkOut,
    BookMarkOutAsync,
    InteractionTargetType,
)
from schemas.tokens_schema import accessTokenOut
from services import bookmark_services, user_service


def test_bookmark_out_async_validates_from_model_instance():
    user_id = "a" * 24
    target_id = "b" * 24

    bookmark = BookMarkOut(
        userId=user_id,
        targetType=InteractionTargetType.page,
        targetId=target_id,
        pageId=target_id,
    )

    converted = BookMarkOutAsync.model_validate(bookmark)

    assert converted.userId == user_id
    assert converted.targetId == target_id
    assert converted.targetType == InteractionTargetType.page


def test_create_bookmark_for_target_returns_async_response_model(monkeypatch):
    user_id = "c" * 24
    target_id = "d" * 24

    async def fake_get_bookmark_by_user_target(*args, **kwargs):
        return None

    async def fake_build_bookmark_model(*args, **kwargs):
        return BookMarkCreate(
            userId=user_id,
            targetType=InteractionTargetType.page,
            targetId=target_id,
            pageId=target_id,
        )

    async def fake_create_bookmark(*args, **kwargs):
        return {
            "_id": "e" * 24,
            "userId": user_id,
            "targetType": InteractionTargetType.page.value,
            "targetId": target_id,
            "pageId": target_id,
            "chapterId": "f" * 24,
            "chapterLabel": "Chapter 1",
        }

    monkeypatch.setattr(bookmark_services, "get_bookmark_by_user_target", fake_get_bookmark_by_user_target)
    monkeypatch.setattr(bookmark_services, "_build_bookmark_model", fake_build_bookmark_model)
    monkeypatch.setattr(bookmark_services, "create_bookmark", fake_create_bookmark)

    async def run_test():
        request = BookMarkCreateRequest(targetType=InteractionTargetType.page, targetId=target_id)
        return await bookmark_services.create_bookmark_for_target(userId=user_id, request=request)

    created = asyncio.run(run_test())

    assert isinstance(created, BookMarkOutAsync)
    assert created.userId == user_id
    assert created.targetId == target_id


def test_create_bookmark_for_target_returns_409_for_duplicates(monkeypatch):
    user_id = "1" * 24
    target_id = "2" * 24

    async def fake_get_bookmark_by_user_target(*args, **kwargs):
        return {"_id": "3" * 24, "userId": user_id, "targetId": target_id}

    monkeypatch.setattr(bookmark_services, "get_bookmark_by_user_target", fake_get_bookmark_by_user_target)

    async def run_test():
        request = BookMarkCreateRequest(targetType=InteractionTargetType.page, targetId=target_id)
        await bookmark_services.create_bookmark_for_target(userId=user_id, request=request)

    with pytest.raises(HTTPException) as err:
        asyncio.run(run_test())

    assert err.value.status_code == 409


def test_get_user_details_with_access_token_includes_bookmarks_and_likes(monkeypatch):
    user_id = "4" * 24
    fake_token_out = accessTokenOut.model_validate(
        {"_id": "9" * 24, "userId": user_id, "dateCreated": "2024-01-01T00:00:00+00:00"}
    )

    async def fake_get_access_tokens(*args, **kwargs):
        return fake_token_out

    async def fake_get_user_by_user_id(*args, **kwargs):
        return {
            "_id": user_id,
            "email": "reader@example.com",
            "firstName": "Reader",
            "lastName": "One",
        }

    async def fake_retrieve_user_bookmark(*args, **kwargs):
        return [
            {
                "_id": "5" * 24,
                "userId": user_id,
                "targetType": InteractionTargetType.page.value,
                "targetId": "6" * 24,
                "pageId": "6" * 24,
            }
        ]

    async def fake_retrieve_user_likes(*args, **kwargs):
        return [
            {
                "_id": "7" * 24,
                "userId": user_id,
                "role": "member",
                "chapterId": "8" * 24,
                "chapaterLabel": "Chapter 8",
            }
        ]

    monkeypatch.setattr(user_service, "get_access_tokens", fake_get_access_tokens)
    monkeypatch.setattr(user_service, "get_user_by_userId", fake_get_user_by_user_id)
    monkeypatch.setattr(user_service, "retrieve_user_bookmark", fake_retrieve_user_bookmark)
    monkeypatch.setattr(user_service, "retrieve_user_likes", fake_retrieve_user_likes)

    user = asyncio.run(user_service.get_user_details_with_accessToken(token="token"))

    assert user is not None
    assert len(user.bookmarks) == 1
    assert len(user.likes) == 1
    assert user.bookmarks[0].targetId == "6" * 24
    assert user.likes[0].chapterId == "8" * 24
