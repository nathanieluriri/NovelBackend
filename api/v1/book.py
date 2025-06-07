from fastapi import APIRouter, HTTPException
from schemas.book_schema import BookCreate, BookOut,BookUpdate,BookBase,BookBaseRequest
from typing import List
from services.book_services import add_book,delete_book,fetch_books,change_book_name

router = APIRouter()
@router.get("/get", response_model=List[BookOut])
async def get_all_available_books():
    try:
        books = await fetch_books()
        return books
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=BookOut)
async def create_new_book(book: BookBaseRequest):
    b = BookBase(name=book.name,number=0)
    bo = BookCreate(**b.model_dump())
    try:
        new_book = await add_book(num=bo.number,name=bo.name,)
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

@router.patch("/update/{bookId}",response_model=BookOut)
async def change_a_book_name(bookId:str,book:BookUpdate ):
    try:
        updated_book = await change_book_name(bookId=bookId,book=book)
        return updated_book
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
