from schemas.likes_schema import LikeOut,LikeCreate,LikeBase
from repositories.like_repo import create_like ,delete_like_with_like_id,get_all_user_likes,get_all_chapter_likes
from services.chapter_services import fetch_chapter_with_chapterId
import asyncio

async def add_like(likeData:LikeBase,):
    chapterData=await fetch_chapter_with_chapterId(likeData.chapterId)
    NewLikeData =LikeCreate(**likeData.model_dump(),chapaterLabel=chapterData.chapterLabel,)
    result = await create_like(like_data=NewLikeData)
    
    return LikeOut(**result)
    

async def remove_like(likeId:str):
    result = await delete_like_with_like_id(likeId=likeId)
    return result


async def retrieve_user_likes(userId:str):
    result = await get_all_user_likes(userId=userId)
    list_of_likes = [LikeOut(**likes) for likes in result]
    return list_of_likes

async def retrieve_chapter_likes(chapterId:str):
    result = await get_all_chapter_likes(chapterId=chapterId)
    list_of_likes = [LikeOut(**likes) for likes in result]
    return list_of_likes


