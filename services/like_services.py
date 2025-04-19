from schemas.likes_schema import LikeOut,LikeCreate
from repositories.like_repo import create_like ,delete_like_with_like_id,get_all_user_likes
import asyncio

async def add_like(userId:str,pageId:str):
    result = await create_like(like_data=LikeCreate(userId=userId,pageId=pageId))
    return result
    

async def remove_like(likeId:str):
    result = await delete_like_with_like_id(likeId=likeId)
    return result


async def retrieve_user_likes(userId:str):
    result = await get_all_user_likes(userId=userId)
    list_of_likes = [LikeOut(**likes) for likes in result]
    return list_of_likes

# asyncio.run(add_book(num=1,name="Mrs. Bee"))
# asyncio.run(delete_book(bookId="6802f901b04928b8a0589600"))