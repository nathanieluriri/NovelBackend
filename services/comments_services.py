from schemas.comments_schema import CommentOut,CommentCreate
from repositories.comments_repo import create_comment ,delete_comment_with_comment_id,get_all_user_comments,get_all_chapter_comments
import asyncio

async def add_Comment(CommentData:CommentCreate):
    result = await create_comment(comment_data=CommentData)
    return result
    

async def remove_Comment(CommentId:str):
    result = await delete_comment_with_comment_id(commentId=CommentId)
    return result


async def retrieve_user_Comments(userId:str):
    result = await get_all_user_comments(userId=userId)
    list_of_Comments = [CommentOut(**Comments) for Comments in result]
    return list_of_Comments

async def retrieve_chapter_Comments(chapterId:str):
    result = await get_all_chapter_comments(chapterId=chapterId)
    list_of_Comments = [CommentOut(**Comments) for Comments in result]
    return list_of_Comments


