from repositories.book_repo import get_all_books,get_all_books_by_name,get_book_by_number,create_book,get_book_by_book_id,delete_book_with_bookId,update_book_order_after_delete,update_book
from repositories.page_repo import delete_pages_with_chapter_ids
from repositories.chapter_repo import delete_chapters_with_book_id
from schemas.book_schema import BookCreate,BookOut,BookUpdate
import asyncio

async def add_book(num:int,name:str):
    
    all_books= await get_all_books()
    print(len(all_books))
    if len(all_books)!=0:
        all_books_with_same_name= get_all_books_by_name(name=name,books=all_books)
        retrieved_book = get_book_by_number(number=num,books=all_books,name=name)
    elif len(all_books)==0:
        retrieved_book=None
        
    if retrieved_book==None:
        book =await create_book(book_data=BookCreate(name=f"{name}",number=len(all_books)+1))
        return book
        
    elif retrieved_book!=None and retrieved_book.get("name",None)==name:
        book =await create_book(book_data=BookCreate(name=f"{name}{len(all_books_with_same_name)}",number=len(all_books)+1))
        return book
        
    elif retrieved_book!=None and retrieved_book.get("name",None)!=name:
        book =await create_book(book_data=BookCreate(name=name,number=len(all_books)+1))
        return book


async def delete_book(bookId):
    book = await get_book_by_book_id(bookId=bookId)
    if book:
        await delete_chapters_with_book_id(bookId=bookId)
        if book.get("chapters"):
            await delete_pages_with_chapter_ids(chapterIds=book.get('chapters',[]))
        result = await delete_book_with_bookId(bookId=bookId)
        await update_book_order_after_delete(deleted_position=book.get('number'))
        return BookOut(**result)
    return None


async def fetch_books():
    books = await get_all_books()
    list_of_books = [BookOut(**book) for book in books]
    return list_of_books


async def change_book_name(bookId,book:BookUpdate):
     updated_book = await update_book(book_id=bookId,update_data=book)
     return_data = BookOut(**updated_book)
     return return_data
# asyncio.run(add_book(num=1,name="Mrs. Bee"))
# asyncio.run(delete_book(bookId="6802f901b04928b8a0589600"))