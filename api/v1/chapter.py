from fastapi import APIRouter, HTTPException,Depends, UploadFile, Form,File,Body
from security.auth import verify_admin_token
from schemas.chapter_schema import ChapterCreate, ChapterOut,ChapterBase,ChapterUpdateStatusOrLabel,ChapterBaseRequest,ChapterUpdateStatusOrLabelRequest
from typing import List
from services.chapter_services import add_chapter,delete_chapter,fetch_chapters,update_chapter_status_or_label,fetch_chapter_with_chapterId,fetch_chapter_with_chapterNumber_and_bookId
from services.image_service import upload_base64_image,get_base64_from_upload

router = APIRouter()


@router.get("/get/allChapters/{bookId}", response_model=List[ChapterOut],response_model_exclude_none=True)
async def get_all_available_chapters(bookId:str):
    try:
        chapters = await fetch_chapters(bookId=bookId)
        return chapters
    except Exception as e:
        print(e)
        raise 
 
 
@router.get("/get/chapterId/{chapterId}", response_model=ChapterOut,response_model_exclude_none=True)
async def get_specific_chapter_details_with_chapterId(chapterId:str):
    try:
        chapter =await fetch_chapter_with_chapterId(chapterId=chapterId)
        return chapter
    except Exception as e:
        print(e)
        raise 
 
 
@router.get("/get/{bookId}/{chapterNumber}", response_model=ChapterOut,response_model_exclude_none=True)
async def get_specific_chapter_details_with_number_and_bookId(bookId:str,chapterNumber:int):
    try:
        chapter = await fetch_chapter_with_chapterNumber_and_bookId(bookId=bookId,chapterNumber=chapterNumber)
        return chapter
    except Exception as e:
        print(e)
        raise 
 

@router.post("/create", response_model=ChapterOut,dependencies=[Depends(verify_admin_token)],response_model_exclude_none=True)
async def create_a_new_chapter(chapter: ChapterBaseRequest):
    chapter= ChapterCreate(**chapter.model_dump())
    try:
        new_chapter = await add_chapter(chapter=chapter)
        return new_chapter
    except Exception as e:
        print(e)
        raise 

@router.delete("/delete/{chapterId}",response_model=ChapterOut,dependencies=[Depends(verify_admin_token)],response_model_exclude_none=True)
async def delete_a_chapter(chapterId:str ):
    try:
        deleted_chapter = await delete_chapter(chapterId=chapterId)
        return deleted_chapter
    except Exception as e:
        print(e)
        raise 

@router.patch("/update/{chapterId}",response_model_exclude_defaults=True,response_model=ChapterOut,dependencies=[Depends(verify_admin_token)],response_model_exclude_none=True)
async def update_a_chapter(chapterId:str, chapterDetails: ChapterUpdateStatusOrLabelRequest ):
    
    updateChapter = ChapterUpdateStatusOrLabel(**chapterDetails.model_dump())
    try:
        updated_chapter = await update_chapter_status_or_label(chapterId=chapterId,chapter=updateChapter)
        return updated_chapter
    except Exception as e:
        print(e)
        raise 