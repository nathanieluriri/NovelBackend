from schemas.comments_schema import CommentOut,CommentCreate,UpdateCommentBaseRequest
from repositories.comments_repo import create_comment ,delete_comment_with_comment_id,get_all_user_comments,get_all_chapter_comments,delete_comment_with_comment_id_userId,update_comment_with_comment_id
import asyncio

async def add_Comment(CommentData:CommentCreate):
    result = await create_comment(comment_data=CommentData)
    comment = CommentOut(**result)
    await comment.model_async_validate()
    return result
    

async def remove_Comment(CommentId:str):
    result = await delete_comment_with_comment_id(commentId=CommentId)
    return result

async def remove_Comment_by_userId_and_commentId(CommentId:str,userId):
    result = await delete_comment_with_comment_id_userId(userId=userId,commentId=CommentId)
    return result

async def update_comment(commentId:str,userId:str,text:str):
    updated_comment = await update_comment_with_comment_id(commentId=commentId,userId=userId,text=text)
    await updated_comment.model_async_validate()
    return CommentOut(**updated_comment)


async def retrieve_user_Comments(userId:str):
    result = await get_all_user_comments(userId=userId)
    list_of_Comments=[]
    for comment in result:
        Comment =CommentOut(**comment)
        await Comment.model_async_validate()
        list_of_Comments.append(Comment)
    return list_of_Comments

async def retrieve_chapter_Comments(chapterId:str):
    result = await get_all_chapter_comments(chapterId=chapterId)
    list_of_Comments=[]
    for comment in result:
        Comment =CommentOut(**comment)
        await Comment.model_async_validate()
        list_of_Comments.append(Comment)
    return list_of_Comments


