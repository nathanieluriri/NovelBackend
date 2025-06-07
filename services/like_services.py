from schemas.likes_schema import LikeOut,LikeCreate
from repositories.like_repo import create_like ,delete_like_with_like_id,get_all_user_likes,get_all_chapter_likes
import asyncio

async def add_like(userId:str,chapterId:str):
    result = await create_like(like_data=LikeCreate(userId=userId,chapterId=chapterId))
    return result
    

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


