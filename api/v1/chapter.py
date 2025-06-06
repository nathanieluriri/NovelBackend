from fastapi import APIRouter, HTTPException,Depends, UploadFile, Form,File,Body
from security.auth import verify_admin_token
from schemas.chapter_schema import ChapterCreate, ChapterOut,ChapterBase,ChapterUpdateStatusOrLabel
from typing import List
from services.chapter_services import add_chapter,delete_chapter,fetch_chapters,update_chapter_status_or_label
from services.image_service import upload_base64_image,get_base64_from_upload
router = APIRouter()


@router.get("/get/{bookId}", response_model=List[ChapterOut])
async def get_all_available_chapters(bookId:str):
    try:
        chapters = await fetch_chapters(bookId=bookId)
        return chapters
    except Exception as e:
        print(e)
        raise 
 

@router.post("/create", response_model=ChapterOut,dependencies=[Depends(verify_admin_token)])
async def create_a_new_chapter(chapter: ChapterBase = Depends(ChapterBase.as_form),coverImage: UploadFile = File(...)):
    chapter= ChapterCreate(**chapter.model_dump())
    base_64_image = await get_base64_from_upload(coverImage)
    chapter.coverImage=await upload_base64_image(base64_string=base_64_image)
    try:
        new_chapter = await add_chapter(chapter=chapter)
        return new_chapter
    except Exception as e:
        print(e)
        raise 

@router.delete("/delete/{chapterId}",response_model=ChapterOut,dependencies=[Depends(verify_admin_token)])
async def delete_a_chapter(chapterId:str ):
    try:
        deleted_chapter = await delete_chapter(chapterId=chapterId)
        return deleted_chapter
    except Exception as e:
        print(e)
        raise 

@router.put("/update/{chapterId}",response_model=ChapterOut,dependencies=[Depends(verify_admin_token)])
async def update_a_chapter(chapterId:str,chapterDetails: ChapterUpdateStatusOrLabel = Depends(ChapterUpdateStatusOrLabel.as_form),coverImage: UploadFile = File(...) ):
    try:
        base_64_image = await get_base64_from_upload(coverImage)
        
        chapterDetails.coverImage=await upload_base64_image(base64_string=base_64_image)
        updated_chapter = await update_chapter_status_or_label(chapterId=chapterId,chapter=chapterDetails)
        return updated_chapter
    except Exception as e:
        print(e)
        raise 