from schemas.bookmark_schema import BookMarkCreate,BookMarkOut
from repositories.bookmark_repo import create_bookmark,delete_bookmarks_with_bookmark_id,get_all_user_bookmarks
import asyncio

async def add_bookmark(userId:str,pageId:str):
    result = await create_bookmark(bookmark_data=BookMarkCreate(userId=userId,pageId=pageId))
    return result
    

async def remove_like(bookmarkId:str):
    result = await delete_bookmarks_with_bookmark_id(bookmarkId=bookmarkId)
    return result


async def retrieve_user_likes(userId:str):
    result = await get_all_user_bookmarks(userId=userId)
    list_of_bookmarks = [BookMarkOut(**bookmark) for bookmark in result]
    return list_of_bookmarks


# asyncio.run(add_book(num=1,name="Mrs. Bee"))
# asyncio.run(delete_book(bookId="6802f901b04928b8a0589600"))