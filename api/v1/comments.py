from fastapi import APIRouter, HTTPException,Depends
from security.auth import verify_any_token,verify_admin_token,verify_token
from schemas.comments_schema import CommentCreate, CommentOut,CommentBaseRequest,UpdateCommentBaseRequest
from typing import List
from services.comments_services import add_Comment,remove_Comment,retrieve_user_Comments,retrieve_chapter_Comments,remove_Comment_by_userId_and_commentId,update_comment
from services.user_service import get_user_details_with_accessToken
from services.admin_services import get_admin_details_with_accessToken_service


router = APIRouter()


@router.get("/get", response_model=List[CommentOut],dependencies=[Depends(verify_any_token)])
async def get_all_available_Comments_a_particular_user_made(dep= Depends(verify_any_token)):
    try:
        if dep['role']=='user':
            userDetails =await get_user_details_with_accessToken(token= dep['accessToken'])
            Comments = await retrieve_user_Comments(userId=userDetails.userId)
            return Comments
        elif dep['role']=='admin':
            userDetails =await get_admin_details_with_accessToken_service(token= dep['accessToken'])
            Comments = await retrieve_user_Comments(userId=userDetails.userId)
            return Comments
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/get/{chapterId}", response_model=List[CommentOut])
async def get_all_chapter_Comments(chapterId:str):
    try:
        Comments = await retrieve_chapter_Comments(chapterId=chapterId)
        return Comments
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/create", response_model=CommentOut,dependencies=[Depends(verify_any_token)])
async def Comment_on_a_chapter(Comment: CommentBaseRequest,dep= Depends(verify_any_token)):
    created_Comment = CommentCreate(**Comment.model_dump())
    if dep['role']=='user':
        userDetails =await get_user_details_with_accessToken(token= dep['accessToken'])
        created_Comment.userId=userDetails.userId 
        created_Comment.role=dep['role']
        try:
            new_Comment = await add_Comment(CommentData=created_Comment)
            return new_Comment
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif dep['role'] == 'admin':
        userDetails =await get_admin_details_with_accessToken_service(token= dep['accessToken'])
        created_Comment.userId= userDetails.userId
        created_Comment.role=dep['role']
        try:
            new_Comment = await add_Comment(CommentData=created_Comment)
            return new_Comment
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/remove/{CommentId}",dependencies=[Depends(verify_any_token)], response_model=CommentOut)
async def unComment(CommentId: str,dep=Depends(verify_token)):
    try:
        if dep['role']=='user':
            userDetails =await get_user_details_with_accessToken(token= dep['accessToken'])
            removed_Comment = await remove_Comment_by_userId_and_commentId(CommentId=CommentId,userId=userDetails.userId)
            if removed_Comment:
                return removed_Comment
            else:
                raise HTTPException(status_code=404, detail="Resource already deleted")
        elif dep['role']=='admin':
            userDetails =await get_admin_details_with_accessToken_service(token= dep['accessToken'])
            
            removed_Comment = await remove_Comment_by_userId_and_commentId(CommentId=CommentId,userId=userDetails.userId)
            if removed_Comment:
                return removed_Comment
            else:
                raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (Comment 404s) without changing them
        raise
    except Exception as e:
        # catch all other unknown exceptions
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.delete("/admin/remove/{CommentId}", response_model=CommentOut,dependencies=[Depends(verify_admin_token)])
async def AdminPriveledgeunComment(CommentId: str):
    try:
        removed_Comment = await remove_Comment(CommentId=CommentId)
        if removed_Comment:
            return removed_Comment
        else:
            raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (Comment 404s) without changing them
        raise
    except Exception as e:
        # catch all other unknown exceptions
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.patch("/update",response_model=CommentOut,dependencies=[Depends(verify_any_token)])
async def updateComment(updateData:UpdateCommentBaseRequest,dep=Depends(verify_any_token)):
    try:
        if dep['role']=='user':
            userDetails =await get_user_details_with_accessToken(token= dep['accessToken'])
            updated_comment = await update_comment(commentId=updateData.commentId,userId=userDetails.userId,text=updateData.text)
            if updated_comment:
                return updated_comment
            else:
                raise HTTPException(status_code=404, detail="Resource already deleted")
        elif dep['role']=='admin':
            userDetails =await get_admin_details_with_accessToken_service(token= dep['accessToken'])
            updated_comment = await update_comment(commentId=updateData.commentId,userId=userDetails.userId,text=updateData.text)
            if updated_comment:
                return updated_comment
            else:
                raise HTTPException(status_code=404, detail="Resource already deleted")
    except HTTPException:
        # re-raise known exceptions (Comment 404s) without changing them
        raise
    except Exception as e:
        # catch all other unknown exceptions
        raise HTTPException(status_code=500, detail=str(e))