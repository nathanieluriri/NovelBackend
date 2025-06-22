from schemas.imports import *
from enum import Enum

class CommentType(str,Enum):
    reply_chapter="Reply To Chapter"
    reply_comment ="Reply To Comment"
    reply_reply ="Reply To Reply"

class CommentBaseRequest(BaseModel):
    chapterId: str
    text:str
    commentType:Optional[CommentType]=CommentType.reply_chapter
class UpdateCommentBaseRequest(BaseModel):
    commentId: str
    text:str


class CommentBase(BaseModel):
    userId:str
    role:str
    text:str
    chapterId: str
    commentType:Optional[CommentType]=CommentType.reply_chapter

class CommentCreate(CommentBase):
    userId:Optional[str]=None
    role:Optional[str]=None
    commentType:Optional[CommentType]=CommentType.reply_chapter
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
    
class CommentOut(CommentBase):
    id: Optional[str] =None
    commentType:Optional[CommentType]=CommentType.reply_chapter
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values
    

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }


