from fastapi import APIRouter, BackgroundTasks, HTTPException,Depends
from security.auth import verify_admin_token, verify_any_token
from schemas.page_schema import PageOut,PageBase,PageUpdateRequest
from typing import List
from services.page_services import (
    add_page,
    delete_page,
    fetch_page_for_user,
    update_page_content,
    fetch_single_page_by_pageId_for_user,
)
from services.user_service import get_user_details_with_accessToken
from services.reading_progress_service import track_user_reading_progress
from core.cache_invalidation import invalidate_entity_cache

router = APIRouter()
@router.get("/get/{chapterId}", response_model=List[PageOut])
async def get_all_available_pages(chapterId:str, dep=Depends(verify_any_token)):
    if len(chapterId) != 24:
        raise HTTPException(status_code=400, detail="pageId must be exactly 24 characters long")
    try:
        user_details = await get_user_details_with_accessToken(token=dep["accessToken"])
        if not user_details:
            raise HTTPException(status_code=401, detail="Invalid token")
        pages = await fetch_page_for_user(chapterId=chapterId, user=user_details)
        return pages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



    

@router.get("/get/page/{pageId}", response_model=PageOut)
async def get_particular_page(pageId:str, background_tasks: BackgroundTasks, dep=Depends(verify_any_token)):
    if len(pageId) != 24:
        raise HTTPException(status_code=400, detail="pageeId must be exactly 24 characters long")

    try:
        user_details = await get_user_details_with_accessToken(token=dep["accessToken"])
        if not user_details:
            raise HTTPException(status_code=401, detail="Invalid token")
        page = await fetch_single_page_by_pageId_for_user(pageId=pageId, user=user_details)
        if user_details.userId and page.chapterId:
            background_tasks.add_task(
                track_user_reading_progress,
                user_details.userId,
                page.chapterId,
                pageId,
            )
        return page
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    


@router.post("/create/{bookId}", response_model=PageOut,dependencies=[Depends(verify_admin_token)])
@invalidate_entity_cache(book_arg_names=("bookId",), page_response_fields=("id",), chapter_response_fields=("chapterId",))
async def create_a_new_page(page: PageBase,bookId:str):
    if len(bookId) != 24:
        raise HTTPException(status_code=400, detail="bookId must be exactly 24 characters long")
    try:
        new_page = await add_page(status=page.status,textContent=page.textContent,chapterId=page.chapterId,bookId=bookId)
        return new_page
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{pageId}",dependencies=[Depends(verify_admin_token)])
@invalidate_entity_cache(page_arg_names=("pageId",), page_response_fields=("id",), chapter_response_fields=("chapterId",))
async def delete_a_page(pageId:str ):
    if len(pageId) != 24:
        raise HTTPException(status_code=400, detail="pageId must be exactly 24 characters long")
    try:
        deleted_page = await delete_page(pageId=pageId)
        if deleted_page:
            return deleted_page
        else:
            raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (like 404s) without changing them
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/update/{pageId}",response_model=PageOut,dependencies=[Depends(verify_admin_token)])
@invalidate_entity_cache(page_arg_names=("pageId",), page_response_fields=("id",), chapter_response_fields=("chapterId",))
async def update_a_page(pageId:str ,page: PageUpdateRequest):
    if len(pageId) != 24:
        raise HTTPException(status_code=400, detail="pageId must be exactly 24 characters long")
    try:
        updated_ = await update_page_content(status=page.status,pageId=pageId,textContent=page.textContent)
        if updated_:
            return updated_
        else:
            raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (like 404s) without changing them
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


