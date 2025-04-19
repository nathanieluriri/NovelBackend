from schemas.bookmark_schema import BookMarkCreate,BookMarkOut
from repositories.bookmark_repo import create_bookmark,delete_bookmarks_with_bookmark_id,get_all_user_bookmarks

async def add_bookmark(userId:str,pageId:str):
    result = await create_bookmark(bookmark_data=BookMarkCreate(userId=userId,pageId=pageId))
    return result
    

async def remove_bookmark(bookmarkId:str):
    result = await delete_bookmarks_with_bookmark_id(bookmarkId=bookmarkId)
    if result:
        return BookMarkOut(**result)
    else: return None

async def retrieve_user_bookmark(userId:str):
    result = await get_all_user_bookmarks(userId=userId)
    if result:
        list_of_bookmarks = [BookMarkOut(**bookmark) for bookmark in result]
        return list_of_bookmarks
    else:
        return []
