from fastapi import APIRouter, HTTPException
from schemas.chapter_schema import ChapterCreate, ChapterOut,ChapterBase
from typing import List
from services.chapter_services import add_chapter,delete_chapter,fetch_chapters

router = APIRouter()
@router.get("/get/{bookId}", response_model=List[ChapterOut])
async def get_all_available_chapters(bookId:str):
    try:
        chapters = await fetch_chapters(bookId=bookId)
        return chapters
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=ChapterOut)
async def create_a_new_chapter(chapter: ChapterBase):
    chapter= ChapterCreate(**chapter.model_dump())
    try:
        new_chapter = await add_chapter(bookId=chapter.bookId)
        return new_chapter
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{chapterId}",response_model=ChapterOut)
async def delete_a_chapter(chapterId:str ):
    try:
        deleted_chapter = await delete_chapter(chapterId=chapterId)
        return deleted_chapter
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
