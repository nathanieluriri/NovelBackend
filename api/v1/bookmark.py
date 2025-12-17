from fastapi import APIRouter, HTTPException
from schemas.bookmark_schema import BookMarkCreate, BookMarkOut,BookMarkBase, BookMarkOutAsync
from typing import List
from services.bookmark_services import add_bookmark,remove_bookmark,retrieve_user_bookmark

router = APIRouter()
@router.get("/get/{userId}", response_model=List[BookMarkOutAsync])
async def get_all_available_bookmarks(userId:str):
    try:
        bookmarks = await retrieve_user_bookmark(userId=userId)
        return bookmarks
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create", response_model=BookMarkOut)
async def create_new_book(book: BookMarkBase):
    new_book = await add_bookmark(userId=book.userId,pageId=book.pageId)
    return new_book
    # try:
    #     new_book = await add_bookmark(userId=book.userId,pageId=book.pageId)
    #     return new_book
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

@router.delete("/remove/{bookmarkId}", response_model=BookMarkOut)
async def delete_a_bookmark(bookmarkId: str):
    try:
        removed_bookmark = await remove_bookmark(bookmarkId=bookmarkId)
        if removed_bookmark:
            return removed_bookmark
        else:
            raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (like 404s) without changing them
        raise
    except Exception as e:
        # catch all other unknown exceptions
        raise HTTPException(status_code=500, detail=str(e))