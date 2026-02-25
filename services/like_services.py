from fastapi import HTTPException

from repositories.user_repo import get_users_by_user_ids
from schemas.admin_schema import ChapterInteractionUserOut
from schemas.likes_schema import LikeOut,LikeCreate,LikeBase
from schemas.utils import normalize_datetime_to_iso
from repositories.like_repo import (
    count_chapter_like_users,
    count_likes_by_chapter,
    count_user_likes,
    create_like,
    delete_like_with_like_id,
    get_all_chapter_likes,
    get_chapter_like_user_stats,
    get_all_user_likes,
)
from services.chapter_services import fetch_chapter_with_chapterId
from core.entity_cache import get_chapter_summary


async def _ensure_chapter_exists(chapterId: str):
    chapter = await fetch_chapter_with_chapterId(chapterId)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")


async def _hydrate_chapter_interaction_users(stats_rows: list[dict]) -> list[ChapterInteractionUserOut]:
    user_ids = [str(row.get("_id")) for row in stats_rows if row.get("_id") is not None]
    users = await get_users_by_user_ids(user_ids)
    user_map = {str(user.get("_id")): user for user in users}

    return [
        ChapterInteractionUserOut(
            userId=str(row.get("_id")),
            firstName=user_map.get(str(row.get("_id")), {}).get("firstName"),
            lastName=user_map.get(str(row.get("_id")), {}).get("lastName"),
            email=user_map.get(str(row.get("_id")), {}).get("email"),
            avatar=user_map.get(str(row.get("_id")), {}).get("avatar"),
            interactionCount=int(row.get("interactionCount", 0)),
            lastInteractionAt=normalize_datetime_to_iso(row.get("lastInteractionAt")),
        )
        for row in stats_rows
        if row.get("_id") is not None
    ]

async def add_like(likeData:LikeBase,):
    chapterData=await fetch_chapter_with_chapterId(likeData.chapterId)
    NewLikeData =LikeCreate(**likeData.model_dump(),chapaterLabel=chapterData.chapterLabel,)
    result = await create_like(like_data=NewLikeData)
    like_out = LikeOut(**result)
    if like_out.chapterId:
        like_out.chapterSummary = await get_chapter_summary(like_out.chapterId)
    return like_out
    

async def remove_like(likeId:str):
    result = await delete_like_with_like_id(likeId=likeId)
    if result is None:
        return None
    like_out = LikeOut(**result)
    if like_out.chapterId:
        like_out.chapterSummary = await get_chapter_summary(like_out.chapterId)
    return like_out


async def retrieve_user_likes(userId:str, skip: int = 0, limit: int | None = None):
    result = await get_all_user_likes(userId=userId, skip=skip, limit=limit)
    list_of_likes = [LikeOut(**likes) for likes in result]
    for like in list_of_likes:
        if like.chapterId:
            like.chapterSummary = await get_chapter_summary(like.chapterId)
    return list_of_likes

async def retrieve_chapter_likes(chapterId:str, skip: int = 0, limit: int | None = None):
    result = await get_all_chapter_likes(chapterId=chapterId, skip=skip, limit=limit)
    list_of_likes = [LikeOut(**likes) for likes in result]
    chapter_summary = await get_chapter_summary(chapterId)
    for like in list_of_likes:
        like.chapterSummary = chapter_summary
    return list_of_likes


async def retrieve_user_likes_count(userId: str) -> int:
    return await count_user_likes(userId=userId)


async def retrieve_chapter_likes_count(chapterId: str) -> int:
    return await count_likes_by_chapter(chapterId=chapterId)


async def retrieve_chapter_like_users(chapterId: str, skip: int = 0, limit: int = 20) -> list[ChapterInteractionUserOut]:
    await _ensure_chapter_exists(chapterId)
    stats = await get_chapter_like_user_stats(chapterId=chapterId, skip=skip, limit=limit)
    return await _hydrate_chapter_interaction_users(stats)


async def retrieve_chapter_like_users_count(chapterId: str) -> int:
    await _ensure_chapter_exists(chapterId)
    return await count_chapter_like_users(chapterId=chapterId)


