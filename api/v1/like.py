from fastapi import APIRouter, HTTPException
from schemas.likes_schema import LikeCreate, LikeOut
from typing import List
from services.like_services import add_like,remove_like,retrieve_user_likes

router = APIRouter()
@router.get("/get/{userId}", response_model=List[LikeOut])
async def get_all_available_likes(userId:str):
    try:
        likes = await retrieve_user_likes(userId=userId)
        return likes
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create", response_model=LikeOut)
async def like_Page(like: LikeOut):
    try:
        new_like = await add_like(userId=like.userId,pageId=like.pageId)
        return new_like
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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