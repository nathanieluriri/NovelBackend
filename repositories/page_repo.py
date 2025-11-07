from core.database import db
from schemas.page_schema import PageCreate,PageUpdate,PageOut
from bson import ObjectId,errors
import asyncio
async def get_all_pages(chapterId):
    cursor= db.pages.find({"chapterId":chapterId})
    retrieved_pages= [chapters async for chapters in cursor]
    return retrieved_pages


async def get_page_by_page_number(number: int,chapterId:str):
    return await db.pages.find_one({"number": number,"chapterId":chapterId})

async def get_page_by_page_id(pageId: str):
    try:
        obj_id = ObjectId(pageId)
    except errors.InvalidId:
        return None
    return await db.pages.find_one({"_id": ObjectId(pageId)})


async def delete_page_with_page_id(pageId: str):
    try:
        obj_id = ObjectId(pageId)
    except errors.InvalidId:
        return None  # or raise an error / log it
    return await db.pages.find_one_and_delete({"_id": obj_id})

async def delete_pages_with_chapter_ids(chapterIds: list):
    if len(chapterIds)>0:
     
        result = await db.pages.delete_many({"chapterId": {"$in": chapterIds}})
        return result
    else:
        print("no pages in this book")
        return None



async def update_page_order_after_delete(deleted_position:int,chapterId:str):
    return await db.pages.update_many(
        
    {   "chapterId":chapterId,
        "number": {"$gt": deleted_position}
    }, 
    {"$inc": {"number": -1}}  
)

async def delete_pages_by_chapter_id(chapter_id: str):
    try:
        obj_id = ObjectId(chapter_id)
    except errors.InvalidId:
        return None  # or raise an error / log it
    result = await db.pages.delete_many({"chapter_id": chapter_id})
    return result.deleted_count  # optional: returns how many were deleted


async def create_page(page_data: PageCreate):
    page = page_data.model_dump()
    result = await db.pages.insert_one(page)
    created_page = await db.pages.find_one({"_id": result.inserted_id})
    return created_page

async def update_page(page_id: str, update_data: PageUpdate):
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict.pop("id",None)
    result = await db.pages.update_one(
        {"_id": ObjectId(page_id)},
        {"$set": update_dict}
    )

    if result.modified_count == 0:
        return {"message": "No changes made or chapter not found."}

    updated_page_value = await db.pages.find_one({"_id": ObjectId(page_id)})
    return updated_page_value


async def get_pages_by_chapter_id(chapterId):
    try:
        obj_id = ObjectId(chapterId)
    except errors.InvalidId:
        return None 
    cursor =  db.pages.find({"chapterId":chapterId})
    pages = [page async for page in cursor]
    return pages
