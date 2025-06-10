from schemas.imports import *


class CommentBaseRequest(BaseModel):
    chapterId: str
    text:str
    
class UpdateCommentBaseRequest(BaseModel):
    commentId: str
    text:str


class CommentBase(BaseModel):
    userId:str
    role:str
    text:str
    chapterId: str


class CommentCreate(CommentBase):
    userId:Optional[str]=None
    role:Optional[str]=None
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
    
class CommentOut(CommentBase):
    id: Optional[str] =None
    
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


