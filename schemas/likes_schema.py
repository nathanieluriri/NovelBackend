import time

from schemas.imports import *
from enum import Enum

class LikeType(str,Enum):
    Like_chapter="Liked Chapter"
    Like_comment ="Liked Comment"
    Like_comment_reply ="Liked Comment Reply"
    Like_reply_reply ="Liked Reply To Reply"


class LikeBaseRequest(BaseModel):
    chapterId: str
    

class LikeBase(LikeBaseRequest):
    userId:str
    role:str
    likeType:Optional[LikeType]=LikeType.Like_chapter


class LikeCreate(LikeBase):
    chapaterLabel:str
 
    dateCreated: Optional[int] = Field(default_factory=lambda: int(time.time()))
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        
        if values['dateCreated']==None:
            values['dateCreated']= now_str
        return values
    
    
class LikeOut(LikeCreate):
    id: Optional[str] =None
 
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values
    

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }


