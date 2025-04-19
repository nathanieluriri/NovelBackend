from core.database import db
from schemas.book_schema import BookCreate,BookUpdate,BookOut
from bson import ObjectId,errors
import asyncio
import re

def get_book_by_number(number: int,name:str,books:list):
    retrieved_books= [books_with_same_name_and_number for books_with_same_name_and_number in books if( re.findall(r'[\w\s!?,\'\.-]+(?=\s*\d*$)|\d+$', books_with_same_name_and_number.get('name'))[0]==name and books_with_same_name_and_number.get('number')==number)]
    if len(retrieved_books)==0:
        return None
    return retrieved_books[0]

async def get_all_books():
    cursor= db.books.find()
    retrieved_books = [books async for books in cursor]
    return retrieved_books

def get_all_books_by_name(name:str,books:list):
    books_with_same_name= [books_with_same_name for books_with_same_name in books if re.findall(r'[\w\s!?,\'\.-]+(?=\s*\d*$)|\d+$', books_with_same_name.get('name'))[0] ==name]
    return books

async def get_book_by_book_id(bookId:str):
    try:
        obj_id = ObjectId(bookId)
    except errors.InvalidId:
        return None
    return await db.books.find_one({"_id": ObjectId(bookId)})

async def create_book(book_data: BookCreate):
    book = book_data.model_dump()
    result = await db.books.insert_one(book)
    created_book = await db.books.find_one({"_id": result.inserted_id})
    return created_book


async def update_book(book_id: str, update_data: BookUpdate):
    update_dict = {k: v for k, v in update_data.model_dump(exclude_none=True).items() if v is not None}
    update_dict.pop("id",None)
    result = await db.books.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": update_dict}
    )

    if result.modified_count == 0:
        return {"message": "No changes made or chapter not found."}

    updated_book_value = await db.books.find_one({"_id": ObjectId(book_id)})
    return updated_book_value



async def delete_book_with_bookId(bookId:str):
    try:
        obj_id = ObjectId(bookId)
    except errors.InvalidId:
        return None
    result = await db.books.find_one_and_delete({"_id":ObjectId(bookId)})
  
    return result


async def update_book_order_after_delete(deleted_position:int):
    return await db.books.update_many(
    {   
        "number": {"$gt": deleted_position}
    },  # only items after the deleted one
    {"$inc": {"number": -1}}                # shift them up
)
