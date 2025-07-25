from schemas.imports import *
from enum import Enum

class LikeType(str,Enum):
    Like_chapter="Liked Chapter"
    Like_comment ="Liked Comment"
    Like_comment_reply ="Liked Comment Reply"
    Like_reply_reply ="Liked Reply To Reply"


class LikeBaseRequest(BaseModel):
    chapterId: str
    likeType:Optional[LikeType]=LikeType.Like_chapter

class LikeBase(LikeBaseRequest):
    userId:str
    role:str


class LikeCreate(LikeBase):
    userId:Optional[str]=None
    role:Optional[str]=None
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
    
class LikeOut(LikeBase):
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


