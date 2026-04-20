import re

from core.database import client, maybe_id
from schemas.book_schema import BookCreate, BookUpdate


BOOKS = "books"


# Kept as pure-Python utilities for callers that already have the full list
# in memory. They do not issue DB queries.
def get_book_by_number(number: int, name: str, books: list):
    pattern = r"[\w\s!?,\'\.-]+(?=\s*\d*$)|\d+$"
    matches = [
        book
        for book in books
        if re.findall(pattern, book.get("name"))[0] == name
        and book.get("number") == number
    ]
    if not matches:
        return None
    return matches[0]


def get_all_books_by_name(name: str, books: list):
    # Preserves legacy behaviour: returns all books. Kept for backward
    # compatibility with callers that depend on this shape.
    del name
    return books


async def get_all_books():
    return await client.find_many(BOOKS)


async def get_all_books_paginated(skip: int = 0, limit: int = 20):
    return await client.find_many(BOOKS, skip=skip, limit=limit)


async def count_all_books() -> int:
    return await client.count(BOOKS)


async def get_book_by_book_id(bookId: str):
    oid = maybe_id(bookId)
    if oid is None:
        return None
    return await client.find_one(BOOKS, {"_id": oid})


async def create_book(book_data: BookCreate):
    return await client.insert_and_fetch(BOOKS, book_data.model_dump())


async def update_book(book_id: str, update_data: BookUpdate):
    oid = maybe_id(book_id)
    if oid is None:
        return {"message": "Invalid book id."}

    update_dict = {
        k: v
        for k, v in update_data.model_dump(exclude_none=True).items()
        if v is not None
    }
    update_dict.pop("id", None)
    modified = await client.update_one(
        BOOKS, {"_id": oid}, {"set": update_dict}
    )
    if modified == 0:
        return {"message": "No changes made or chapter not found."}
    return await client.find_one(BOOKS, {"_id": oid})


async def delete_book_with_bookId(bookId: str):
    oid = maybe_id(bookId)
    if oid is None:
        return None
    return await client.find_one_and_delete(BOOKS, {"_id": oid})


async def update_book_order_after_delete(deleted_position: int):
    # Shift all books positioned after the deleted one up by 1.
    return await client.update_many(
        BOOKS,
        {"number": {"$gt": deleted_position}},
        {"inc": {"number": -1}},
    )
