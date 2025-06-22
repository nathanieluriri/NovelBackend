from fastapi import APIRouter, HTTPException,Depends
from security.auth import verify_admin_token
from schemas.page_schema import PageOut,PageBase,PageUpdateRequest
from typing import List
from services.page_services import add_page,delete_page,fetch_page,update_page_content,fetch_single_page,fetch_single_page_by_pageId

router = APIRouter()
@router.get("/get/{chapterId}", response_model=List[PageOut])
async def get_all_available_pages(chapterId:str):
    if len(chapterId) != 24:
        raise HTTPException(status_code=400, detail="pageId must be exactly 24 characters long")
    try:
        pages = await fetch_page(chapterId=chapterId)
        return pages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



    

@router.get("/get/page/{pageId}", response_model=PageOut)
async def get_particular_page(pageId:str):
    if len(pageId) != 24:
        raise HTTPException(status_code=400, detail="pageeId must be exactly 24 characters long")

    try:
        pages = await fetch_single_page_by_pageId(pageId=pageId)
        return pages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    


@router.post("/create/{bookId}", response_model=PageOut,dependencies=[Depends(verify_admin_token)])
async def create_a_new_page(page: PageBase,bookId:str):
    if len(bookId) != 24:
        raise HTTPException(status_code=400, detail="bookId must be exactly 24 characters long")
    try:
        new_page = await add_page(status=page.status,textContent=page.textContent,chapterId=page.chapterId,bookId=bookId)
        return new_page
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{pageId}",dependencies=[Depends(verify_admin_token)])
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


