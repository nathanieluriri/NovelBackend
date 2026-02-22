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
 
    dateCreated: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    @model_validator(mode='before')
    def set_dates(cls,values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values

        normalized = dict(values)
        now_str = datetime.now(timezone.utc).isoformat()
        date_created = normalized.get("dateCreated")

        if date_created is None:
            normalized["dateCreated"] = now_str
        elif isinstance(date_created, (int, float)):
            normalized["dateCreated"] = datetime.fromtimestamp(date_created, tz=timezone.utc).isoformat()
        else:
            normalized["dateCreated"] = str(date_created)
        return normalized
    
    
class LikeOut(LikeCreate):
    id: Optional[str] =None
 
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values

        normalized = dict(values)
        if normalized.get("id") is None and normalized.get("_id") is not None:
            normalized["id"] = str(normalized.get("_id"))
        return normalized
    

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }


