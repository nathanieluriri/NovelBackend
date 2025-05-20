from fastapi import APIRouter, HTTPException,Depends
from security.auth import verify_admin_token
from schemas.page_schema import PageOut,PageBase,PageUpdateRequest
from typing import List
from services.page_services import add_page,delete_page,fetch_page,update_page_content

router = APIRouter()
@router.get("/get/{chapterId}", response_model=List[PageOut])
async def get_all_available_pages(chapterId:str):
    try:
        pages = await fetch_page(chapterId=chapterId)
        return pages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create/{bookId}", response_model=PageOut,dependencies=[Depends(verify_admin_token)])
async def create_a_new_page(page: PageBase,bookId:str):
   
    try:
        new_page = await add_page(textContent=page.textContent,chapterId=page.chapterId,bookId=bookId)
        return new_page
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{pageId}",response_model=PageOut,dependencies=[Depends(verify_admin_token)])
async def delete_a_page(pageId:str ):
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
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/update/{pageId}",response_model=PageOut,dependencies=[Depends(verify_admin_token)])
async def update_a_page(pageId:str ,page: PageUpdateRequest):
    try:
        updated_ = await update_page_content(pageId=pageId,textContent=page.textContent)
        if updated_:
            return updated_
        else:
            raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (like 404s) without changing them
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
