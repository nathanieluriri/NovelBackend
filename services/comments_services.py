from fastapi import HTTPException

from repositories.book_repo import get_book_by_book_id
from repositories.chapter_repo import get_chapter_by_chapter_id
from repositories.comments_repo import (
    count_all_user_comments,
    count_comments_by_target,
    create_comment,
    delete_comment_with_comment_id,
    delete_comment_with_comment_id_userId,
    get_all_user_comments,
    get_comments_by_target,
    update_comment_with_comment_id,
)
from repositories.page_repo import get_page_by_page_id
from schemas.comments_schema import CommentCreate, CommentCreateRequest, CommentOut, InteractionTargetType


async def _ensure_target_exists(targetType: InteractionTargetType, targetId: str):
    if targetType == InteractionTargetType.book:
        target = await get_book_by_book_id(targetId)
    elif targetType == InteractionTargetType.chapter:
        target = await get_chapter_by_chapter_id(targetId)
    else:
        target = await get_page_by_page_id(targetId)

    if target is None:
        raise HTTPException(status_code=404, detail=f"{targetType.value.capitalize()} not found")


async def add_comment_for_target(request: CommentCreateRequest, userId: str, role: str):
    if request.targetType is None or request.targetId is None:
        raise HTTPException(status_code=422, detail="targetType and targetId are required")
    await _ensure_target_exists(request.targetType, request.targetId)
    comment = CommentCreate(
        userId=userId,
        role=role,
        text=request.text,
        targetType=request.targetType,
        targetId=request.targetId,
        parentCommentId=request.parentCommentId,
        commentType=request.commentType,
    )
    result = await create_comment(comment_data=comment)
    out = CommentOut(**result)
    await out.model_async_validate()
    return out


async def remove_comment(commentId: str):
    removed = await delete_comment_with_comment_id(commentId=commentId)
    if removed is None:
        return None
    out = CommentOut(**removed)
    await out.model_async_validate()
    return out


async def remove_comment_by_userId_and_commentId(commentId: str, userId: str):
    removed = await delete_comment_with_comment_id_userId(userId=userId, commentId=commentId)
    if removed is None:
        return None
    out = CommentOut(**removed)
    await out.model_async_validate()
    return out


async def update_comment(commentId: str, userId: str, text: str):
    updated = await update_comment_with_comment_id(commentId=commentId, userId=userId, text=text)
    if updated is None:
        return None
    out = CommentOut(**updated)
    await out.model_async_validate()
    return out


async def retrieve_user_comments(userId: str, skip: int = 0, limit: int = 20):
    comments = await get_all_user_comments(userId=userId, skip=skip, limit=limit)
    out = []
    for comment in comments:
        item = CommentOut(**comment)
        await item.model_async_validate()
        out.append(item)
    return out


async def retrieve_target_comments(
    targetType: InteractionTargetType,
    targetId: str,
    skip: int = 0,
    limit: int = 20,
):
    comments = await get_comments_by_target(targetType=targetType, targetId=targetId, skip=skip, limit=limit)
    out = []
    for comment in comments:
        item = CommentOut(**comment)
        await item.model_async_validate()
        out.append(item)
    return out


async def retrieve_user_comments_count(userId: str) -> int:
    return await count_all_user_comments(userId=userId)


async def retrieve_target_comments_count(
    targetType: InteractionTargetType,
    targetId: str,
) -> int:
    return await count_comments_by_target(targetType=targetType, targetId=targetId)


# Compatibility wrappers used by legacy routes/imports.
async def add_Comment(CommentData: CommentCreate):
    request = CommentCreateRequest(
        text=CommentData.text,
        targetType=CommentData.targetType,
        targetId=CommentData.targetId,
        parentCommentId=CommentData.parentCommentId,
        commentType=CommentData.commentType,
    )
    return await add_comment_for_target(request=request, userId=CommentData.userId, role=CommentData.role)


async def remove_Comment(CommentId: str):
    return await remove_comment(commentId=CommentId)


async def retrieve_user_Comments(userId: str):
    return await retrieve_user_comments(userId=userId)


async def retrieve_chapter_Comments(chapterId: str):
    return await retrieve_target_comments(targetType=InteractionTargetType.chapter, targetId=chapterId)


async def remove_Comment_by_userId_and_commentId(CommentId: str, userId: str):
    return await remove_comment_by_userId_and_commentId(commentId=CommentId, userId=userId)
