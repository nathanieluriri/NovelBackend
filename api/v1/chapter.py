from fastapi import APIRouter, HTTPException
from schemas.chapter_schema import ChapterCreate, ChapterOut
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
async def create_a_new_chapter(book: ChapterCreate):
    try:
        new_book = await add_chapter(bookId=book.bookId)
        return new_book
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{chapterId}",response_model=ChapterOut)
async def delete_a_chapter(chapterId:str ):
    try:
        new_book = await delete_chapter(chapterId=chapterId)
        return new_book
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
