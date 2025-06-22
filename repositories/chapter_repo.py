from core.database import db
from schemas.chapter_schema import ChapterCreate, ChapterOut,ChapterUpdate
from fastapi import HTTPException
from bson import ObjectId,errors
import asyncio

async def get_chapter_by_bookId(bookId:str):
    try:
        obj_id= ObjectId(bookId)
    except errors.InvalidId:
        raise HTTPException(status_code=500,detail="Invalid Book Id")

    
    cursor= db.chapters.find({"bookId":bookId})
    retrieved_chapters= [chapters async for chapters in cursor]

    return retrieved_chapters

async def get_chapter_by_chapter_id(chapterId:str):
    try:
        obj_id = ObjectId(chapterId)
    except errors.InvalidId:
        return None
    return await db.chapters.find_one({"_id": ObjectId(chapterId)})


async def get_chapter_by_bookid_and_chapter_numer(bookId:str,chapterNumber:int):
    try:
        obj_id = ObjectId(bookId)
    except errors.InvalidId:
        return None
    return await db.chapters.find_one({"bookId": bookId,"number":chapterNumber})



async def get_chapter_by_number(number: int,chapters:list):
    chapter = [chapter_by_number  for chapter_by_number in chapters if chapter_by_number.get('number')==number ]
    return chapter[0]


async def update_chapter_order_after_delete(deleted_position:int,bookId):
    return await db.chapters.update_many(
    {   "bookId":bookId,
        "number": {"$gt": deleted_position}
    },  # only items after the deleted one
    {"$inc": {"number": -1}}                # shift them up
)


async def get_chapter_by_chapterId(chapterId: int,chapters:list):
    chapter = [chapter_by_number  for chapter_by_number in chapters if chapter_by_number.get('_id')==chapterId ]
    return chapter[0]

async def create_chapter(chapter_data: ChapterCreate):
    chapter = chapter_data.model_dump()
    result = await db.chapters.insert_one(chapter)
    created_chapter = await db.chapters.find_one({"_id": result.inserted_id})
    return created_chapter

async def update_chapter(chapter_id: str, update_data: ChapterUpdate):
    update_dict = {k: v for k, v in update_data.model_dump(exclude_none=True).items() if v is not None}
    print(update_dict)
    update_dict.pop("id",None)
    result = await db.chapters.update_one(
        {
            "_id": ObjectId(chapter_id)
        },
        {"$set": update_dict}
    )

    if result.modified_count == 0:
        return {"message": "No changes made or chapter not found."}

    updated_chapter_value = await db.chapters.find_one({"_id": ObjectId(chapter_id)})
    return updated_chapter_value



    
async def delete_chapter_with_chapter_id(chapterId):
    try:
        obj_id = ObjectId(chapterId)
    except errors.InvalidId:
        return None 
    return await db.chapters.find_one_and_delete({"_id":ObjectId(chapterId)})


async def delete_chapters_with_book_id(bookId: str):
    try:
        obj_id = ObjectId(bookId)
    except errors.InvalidId:
        return None 
    result = await db.chapters.delete_many({"bookId": bookId})
    return result.deleted_count 


# asyncio.run(delete_chapters_with_book_id(bookId="6802f901b04928b8a0589600"))