from schemas.likes_schema import LikeOut,LikeCreate,LikeBase
from repositories.like_repo import (
    count_likes_by_chapter,
    count_user_likes,
    create_like,
    delete_like_with_like_id,
    get_all_chapter_likes,
    get_all_user_likes,
)
from services.chapter_services import fetch_chapter_with_chapterId
from core.entity_cache import get_chapter_summary
import asyncio

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


