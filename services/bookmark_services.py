from schemas.bookmark_schema import BookMarkCreate,BookMarkOut, BookMarkOutAsync
from repositories.bookmark_repo import create_bookmark,delete_bookmarks_with_bookmark_id,get_all_user_bookmarks
from services.page_services import fetch_single_page_by_pageId
from services.chapter_services import fetch_chapter_with_chapterId


async def add_bookmark(userId:str,pageId:str):
    pageData = await fetch_single_page_by_pageId(pageId=pageId)
    chapterData  = await fetch_chapter_with_chapterId(chapterId=pageData.chapterId)
    bookmark =BookMarkCreate(userId=userId,pageId=pageId,chapterLabel=chapterData.chapterLabel,chapterId=chapterData.id)
    result = await create_bookmark(bookmark_data=bookmark)
    return result
    

async def remove_bookmark(bookmarkId:str):
    result = await delete_bookmarks_with_bookmark_id(bookmarkId=bookmarkId)
    if result:
        return BookMarkOut(**result)
    else: return None


 

async def retrieve_user_bookmark(userId:str):
    bookmarks = await get_all_user_bookmarks(userId=userId)
    list_of_bookmarks=[]
    if bookmarks:
        for bookmark in bookmarks:
            bm = BookMarkOutAsync(**bookmark)
            await bm.model_async_validate()
            list_of_bookmarks.append(bm)
 
        return list_of_bookmarks
    else:
        return []
