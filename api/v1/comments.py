from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from schemas.admin_schema import ChapterInteractionUserOut
from schemas.comments_schema import (
    CommentCreateRequest,
    CommentOut,
    InteractionTargetType,
    UpdateCommentBaseRequest,
)
from security.auth import verify_admin_token, verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.comments_services import (
    add_comment_for_target,
    remove_comment,
    remove_comment_by_userId_and_commentId,
    retrieve_chapter_comment_users,
    retrieve_target_comments,
    retrieve_user_comments,
    update_comment,
)
from services.user_service import get_user_details_with_accessToken


router = APIRouter()


async def _get_actor(dep: dict) -> tuple[str, str]:
    if dep["role"] == "member":
        user = await get_user_details_with_accessToken(token=dep["accessToken"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.userId, dep["role"]

    admin = await get_admin_details_with_accessToken_service(token=dep["accessToken"])
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid token")
    return admin.userId, dep["role"]


@router.get("/get", response_model=List[CommentOut], dependencies=[Depends(verify_any_token)])
async def get_comments(
    targetType: Optional[InteractionTargetType] = None,
    targetId: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    safe_limit = min(max(limit, 1), 100)
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")

    if targetType is not None or targetId is not None:
        if targetType is None or targetId is None:
            raise HTTPException(status_code=400, detail="targetType and targetId must be provided together")
        return await retrieve_target_comments(
            targetType=targetType,
            targetId=targetId,
            skip=skip,
            limit=safe_limit,
        )

    userId, _ = await _get_actor(dep)
    return await retrieve_user_comments(userId=userId, skip=skip, limit=safe_limit)


@router.get("/get/target/{targetType}/{targetId}", response_model=List[CommentOut])
async def get_target_comments(
    targetType: InteractionTargetType,
    targetId: str,
    skip: int = 0,
    limit: int = 20,
):
    safe_limit = min(max(limit, 1), 100)
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    return await retrieve_target_comments(
        targetType=targetType,
        targetId=targetId,
        skip=skip,
        limit=safe_limit,
    )


# Legacy wrapper for chapter-specific query.
@router.get("/get/{chapterId}", response_model=List[CommentOut])
async def get_all_chapter_comments(chapterId: str, skip: int = 0, limit: int = 20):
    safe_limit = min(max(limit, 1), 100)
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    return await retrieve_target_comments(
        targetType=InteractionTargetType.chapter,
        targetId=chapterId,
        skip=skip,
        limit=safe_limit,
    )


@router.get(
    "/admin/get/chapter/{chapterId}/users",
    response_model=List[ChapterInteractionUserOut],
    dependencies=[Depends(verify_admin_token)],
)
async def get_all_chapter_comment_users(chapterId: str):
    return await retrieve_chapter_comment_users(chapterId=chapterId, skip=0, limit=1000)


@router.post("/create", response_model=CommentOut, dependencies=[Depends(verify_any_token)])
async def create_comment(comment: CommentCreateRequest, dep=Depends(verify_any_token)):
    userId, role = await _get_actor(dep)
    return await add_comment_for_target(request=comment, userId=userId, role=role)


@router.delete("/user/remove/{commentId}", dependencies=[Depends(verify_any_token)], response_model=CommentOut)
async def user_remove_comment(commentId: str, dep=Depends(verify_any_token)):
    userId, _ = await _get_actor(dep)
    removed = await remove_comment_by_userId_and_commentId(commentId=commentId, userId=userId)
    if removed is None:
        raise HTTPException(status_code=404, detail="Resource already deleted")
    return removed


@router.delete("/admin/remove/{commentId}", response_model=CommentOut, dependencies=[Depends(verify_admin_token)])
async def admin_remove_comment(commentId: str):
    removed = await remove_comment(commentId=commentId)
    if removed is None:
        raise HTTPException(status_code=404, detail="Resource already deleted")
    return removed


@router.patch("/update", response_model=CommentOut, dependencies=[Depends(verify_any_token)])
async def update_comment_route(updateData: UpdateCommentBaseRequest, dep=Depends(verify_any_token)):
    userId, _ = await _get_actor(dep)
    updated = await update_comment(commentId=updateData.commentId, userId=userId, text=updateData.text)
    if updated is None:
        raise HTTPException(status_code=404, detail="Resource already deleted")
    return updated
