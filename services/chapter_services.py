from repositories.chapter_repo import get_chapter_by_bookId,create_chapter,delete_chapter_with_chapter_id,get_chapter_by_chapter_id,update_chapter_order_after_delete,update_chapter,get_chapter_by_bookid_and_chapter_numer
from repositories.page_repo import delete_pages_by_chapter_id
from repositories.book_repo import update_book
from schemas.book_schema import BookUpdate
from schemas.chapter_schema import ChapterOut,ChapterCreate,ChapterUpdate
from fastapi import HTTPException

async def add_chapter(chapter:ChapterCreate):
    retrieved_chapters = await get_chapter_by_bookId(bookId=chapter.bookId)
    if retrieved_chapters:
        created_chapter =await create_chapter(chapter_data=ChapterCreate(coverImage=chapter.coverImage,bookId=chapter.bookId,chapterLabel=chapter.chapterLabel,status=chapter.status,number=len(retrieved_chapters)+1))
        
        retrieved_chapters = await get_chapter_by_bookId(bookId=chapter.bookId)
        retrieved_chapters_id = [str(ids.get('_id') ) for ids in retrieved_chapters]
        await update_book(book_id=chapter.bookId,update_data=BookUpdate(chapterCount=len(retrieved_chapters),chapters=retrieved_chapters_id))
        chap =ChapterOut(**created_chapter)
        return await chap.model_async_validate()
    else:
        raise HTTPException(status_code=404,detail="Coudn't find a book with such book Id")


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


async def fetch_chapters(bookId: str):
    chapters = await get_chapter_by_bookId(bookId=bookId)
    returnable_chapters = []
    for chapter in chapters:
        chap = ChapterOut(**chapter)
        await chap.model_async_validate()
        returnable_chapters.append(chap)
    return returnable_chapters

async def update_chapter_status_or_label(chapterId:str,chapter:ChapterUpdate):
    await update_chapter(chapter_id=chapterId,update_data=chapter)
    updated_chapter =await get_chapter_by_chapter_id(chapterId=chapterId)
    returnable_chapter =ChapterOut(**updated_chapter) 
    return await returnable_chapter.model_async_validate()


async def fetch_chapter_with_chapterId(chapterId: str):
    chapter = await get_chapter_by_chapter_id(chapterId=chapterId)
    chap = ChapterOut(**chapter)
    
    await chap.model_async_validate()
    return chap



async def fetch_chapter_with_chapterNumber_and_bookId(bookId: str,chapterNumber:int):
    chapter = await get_chapter_by_bookid_and_chapter_numer(bookId=bookId,chapterNumber=chapterNumber)
    chap = ChapterOut(**chapter)
    await chap.model_async_validate()
    return chap
