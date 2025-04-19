from fastapi import APIRouter, HTTPException
from schemas.book_schema import BookCreate, BookOut
from typing import List
from services.book_services import add_book,delete_book,fetch_books

router = APIRouter()
@router.get("/get", response_model=List[BookOut])
async def get_all_available_books():
    try:
        books = await fetch_books()
        return books
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=BookOut)
async def create_new_book(book: BookCreate):
    try:
        new_book = await add_book(num=book.number,name=book.name,)
        return new_book
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete/{bookId}",response_model=BookOut)
async def delete_a_book(bookId:str ):
    try:
        new_book = await delete_book(bookId=bookId)
        return new_book
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
