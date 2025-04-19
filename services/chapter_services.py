from repositories.chapter_repo import get_chapter_by_bookId,create_chapter,delete_chapter_with_chapter_id,get_chapter_by_chapter_id,update_chapter_order_after_delete
from repositories.page_repo import delete_pages_by_chapter_id
from repositories.book_repo import update_book
from schemas.book_schema import BookUpdate
from schemas.chapter_schema import ChapterOut,ChapterCreate
import asyncio

async def add_chapter(bookId:str):
    retrieved_chapters = await get_chapter_by_bookId(bookId=bookId)
    
    created_chapter =await create_chapter(chapter_data=ChapterCreate(bookId=bookId,number=len(retrieved_chapters)+1))
    
    retrieved_chapters = await get_chapter_by_bookId(bookId=bookId)
    retrieved_chapters_id = [str(ids.get('_id') ) for ids in retrieved_chapters]
    await update_book(book_id=bookId,update_data=BookUpdate(chapterCount=len(retrieved_chapters),chapters=retrieved_chapters_id))
    chap =ChapterOut(**created_chapter)
    return chap
    


async def delete_chapter(chapterId:str):
    chapter = await get_chapter_by_chapter_id(chapterId)
    if chapter!=None:
        await delete_pages_by_chapter_id(chapter_id=chapterId)
        result = await delete_chapter_with_chapter_id(chapterId=chapterId)
        await update_chapter_order_after_delete(deleted_position=chapter['number'],bookId=chapter['bookId'])
        retrieved_chapters = await get_chapter_by_bookId(bookId=chapter['bookId'])
        retrieved_chapters_id = [str(ids.get('_id') ) for ids in retrieved_chapters]
        await update_book(book_id=chapter['bookId'],update_data=BookUpdate(chapterCount=len(retrieved_chapters),chapters=retrieved_chapters_id))
        return result
    else:
        print("chapter doesn't exist")

# asyncio.run(add_chapter(bookId="6802f901b04928b8a0589600"))
# asyncio.run(delete_chapter(chapterId="6802a0362897052494193f4a"))
