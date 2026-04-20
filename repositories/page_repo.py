import asyncio

from core.database import ASC, client, is_valid_id, maybe_id
from schemas.page_schema import PageCreate, PageUpdate


PAGES = "pages"


_page_indexes_ready = False
_page_indexes_lock = asyncio.Lock()


async def ensure_page_indexes() -> None:
    global _page_indexes_ready
    if _page_indexes_ready:
        return
    async with _page_indexes_lock:
        if _page_indexes_ready:
            return
        await client.ensure_index(
            PAGES, [("chapterId", ASC), ("number", ASC)], background=True
        )
        _page_indexes_ready = True


async def get_all_pages(chapterId):
    await ensure_page_indexes()
    return await client.find_many(PAGES, {"chapterId": chapterId})


async def get_page_by_page_number(number: int, chapterId: str):
    await ensure_page_indexes()
    return await client.find_one(
        PAGES, {"number": number, "chapterId": chapterId}
    )


async def get_page_by_page_id(pageId: str):
    oid = maybe_id(pageId)
    if oid is None:
        return None
    return await client.find_one(PAGES, {"_id": oid})


async def delete_page_with_page_id(pageId: str):
    oid = maybe_id(pageId)
    if oid is None:
        return None
    return await client.find_one_and_delete(PAGES, {"_id": oid})


async def delete_pages_with_chapter_ids(chapterIds: list):
    if not chapterIds:
        return None
    return await client.delete_many(
        PAGES, {"chapterId": {"$in": chapterIds}}
    )


async def update_page_order_after_delete(deleted_position: int, chapterId: str):
    return await client.update_many(
        PAGES,
        {"chapterId": chapterId, "number": {"$gt": deleted_position}},
        {"inc": {"number": -1}},
    )


async def delete_pages_by_chapter_id(chapter_id: str):
    if not is_valid_id(chapter_id):
        return None
    # Preserves a legacy field name `chapter_id` that may exist on older docs.
    return await client.delete_many(PAGES, {"chapter_id": chapter_id})


async def create_page(page_data: PageCreate):
    return await client.insert_and_fetch(PAGES, page_data.model_dump())


async def update_page(page_id: str, update_data: PageUpdate):
    oid = maybe_id(page_id)
    if oid is None:
        return {"message": "Invalid page id."}

    update_dict = {
        k: v for k, v in update_data.model_dump().items() if v is not None
    }
    update_dict.pop("id", None)
    modified = await client.update_one(
        PAGES, {"_id": oid}, {"set": update_dict}
    )
    if modified == 0:
        return {"message": "No changes made or chapter not found."}
    return await client.find_one(PAGES, {"_id": oid})


async def get_pages_by_chapter_id(
    chapterId, skip: int = 0, limit: int | None = None
):
    if not is_valid_id(chapterId):
        return None
    await ensure_page_indexes()
    return await client.find_many(
        PAGES, {"chapterId": chapterId}, skip=skip, limit=limit
    )


async def count_pages_by_chapter_id(chapterId: str) -> int:
    return await client.count(PAGES, {"chapterId": chapterId})
