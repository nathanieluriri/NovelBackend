from fastapi import APIRouter, HTTPException,Depends
from security.auth import verify_admin_token, verify_any_token
from schemas.admin_schema import ChapterInteractionUserOut
from schemas.likes_schema import LikeCreate, LikeOut,LikeBaseRequest,LikeBase
from typing import List
from services.like_services import (
    add_like,
    remove_like,
    retrieve_chapter_like_users,
    retrieve_chapter_likes,
    retrieve_user_likes,
)
from services.user_service import get_user_details_with_accessToken
from services.admin_services import get_admin_details_with_accessToken_service


router = APIRouter()
@router.get("/get", response_model=List[LikeOut],dependencies=[Depends(verify_any_token)])
async def get_user_likes(dep= Depends(verify_any_token)):
    try:
        if dep['role']=='admin':
            userDetails =await get_admin_details_with_accessToken_service(token= dep['accessToken'])
           
            likes = await retrieve_user_likes(userId=userDetails.userId)
            return likes
        if dep['role']=='member':
            userDetails =await get_user_details_with_accessToken(token= dep['accessToken'])
           
            likes = await retrieve_user_likes(userId=userDetails.userId)
            return likes
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/get/{chapterId}", response_model=List[LikeOut])

async def get_all_chapter_likes(chapterId:str):
    try:
        likes = await retrieve_chapter_likes(chapterId=chapterId)
        return likes
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/admin/get/chapter/{chapterId}/users",
    response_model=List[ChapterInteractionUserOut],
    dependencies=[Depends(verify_admin_token)],
)
async def get_all_chapter_like_users(chapterId: str):
    try:
        return await retrieve_chapter_like_users(chapterId=chapterId, skip=0, limit=1000)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=LikeOut,dependencies=[Depends(verify_any_token)])
async def like_chapter(
    like: LikeBaseRequest,
    dep=Depends(verify_any_token)
):
    access_token = dep.get("accessToken")
    role = dep.get("role")

    # Try getting user or admin details
    user_details = await get_user_details_with_accessToken(token=access_token)
    if not user_details:
        user_details = await get_admin_details_with_accessToken_service(token=access_token)

    if not user_details:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    created_like = LikeBase(
        chapterId=like.chapterId,
        userId=user_details.userId,
        role=role
    )

    try:
        new_like = await add_like(likeData=created_like)
        return new_like
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create like: {e}")
    
    
@router.delete("/remove/{likeId}", response_model=LikeOut)
async def unlike(likeId: str):
    try:
        removed_like = await remove_like(likeId=likeId)
        if removed_like:
            return removed_like
        else:
            raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (like 404s) without changing them
        raise
    except Exception as e:
        # catch all other unknown exceptions
        raise HTTPException(status_code=500, detail=str(e))
