from repositories.page_repo import create_page,get_all_pages,update_page,delete_page_with_page_id,get_page_by_page_id,update_page_order_after_delete,get_pages_by_chapter_id
from schemas.page_schema import PageCreate,PageOut,PageUpdate
from schemas.chapter_schema import ChapterUpdate
from repositories.chapter_repo import update_chapter
import asyncio


async def add_page(bookId,chapterId,textContent):
    pages = await get_all_pages(chapterId=chapterId)
    page = await create_page(page_data=PageCreate(number=len(pages)+1,chapterId=chapterId,textContent=textContent))
    pages = await get_all_pages(chapterId=chapterId)
    page_ids = [str(ids.get("_id")) for ids in pages]
    await update_chapter(chapter_id=chapterId,update_data=ChapterUpdate(pageCount=len(pages),pages=page_ids))
    created_page = PageOut(**page)
    print(created_page)
    return created_page
    
    
async def update_page_content(pageId,textContent):
    result = await update_page(page_id=pageId,update_data=PageUpdate(textContent=textContent))
    
    pages = await get_all_pages(chapterId=result['chapterId'])
    page_ids = [str(ids.get("_id")) for ids in pages]
    
    await update_chapter(chapter_id=result['chapterId'],update_data=ChapterUpdate(pageCount=len(pages),pages=page_ids))
    return result


async def delete_page(pageId):
    page = await get_page_by_page_id(pageId)
    print(page)
    if page!=None:
        result=await delete_page_with_page_id(pageId=pageId)
        update = await update_page_order_after_delete(deleted_position=page['number'],chapterId=page['chapterId'])
        pages = await get_all_pages(chapterId=page['chapterId'])
        page_ids = [str(ids.get("_id")) for ids in pages]
        await update_chapter(chapter_id=result['chapterId'],update_data=ChapterUpdate(pageCount=len(pages),pages=page_ids))
        return PageOut(**result)

    else:
        print("Page doesnt exist")

async def fetch_page(chapterId):
    pages = await get_pages_by_chapter_id(chapterId=chapterId)
    returnable_pages = [PageOut(**page) for page in pages]
    return returnable_pages
