from schemas.imports import *
from core.database import db
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo

class ChapterBaseRequest(BaseModel):
    bookId:str
    chapterLabel:str
    status:str
    coverImage: Optional[str]=None
    
class ChapterBase(ChapterBaseRequest):
    number: Optional[int]=0
    chapterLabel:Optional[str]=None
    status:Optional[str]=None
    
    
class ChapterCreate(ChapterBase):
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    dateUpdated: Optional[str]=None
    pageCount: Optional[int]=0
    pages: Optional[List[str]] = None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        values['dateUpdated']= now_str
        return values

    
    

class ChapterOut(AsyncValidationModelMixin,ChapterBase):
    id: Optional[str] =None
    coverImage: Optional[str]=None
    lastAccessed: Optional[str]=datetime.now(timezone.utc).isoformat()
    dateCreated: Optional[str]=None
    dateUpdated: Optional[str]=None
    pageCount: Optional[int]=0
    pages: Optional[List[str]] = None
    commentsCount:Optional[int]=0
    likesCount:Optional[int]=0
    @async_field_validator('commentsCount','likesCount')
    async def set_counts(self,config: ValidationInfo):
        # Comments Count
        comments_count = await db.comments.aggregate([
            {"$match": {"chapterId": self.id}},
            {"$count": "total"}
        ]).to_list(length=1)

        # Likes Count
        likes_count = await db.likes.aggregate([
            {"$match": {"chapterId": self.id}},
            {"$count": "total"}
        ]).to_list(length=1)

        # Extract count
        comments_count = comments_count[0]["total"] if comments_count else 0
        likes_count = likes_count[0]["total"] if likes_count else 0
        self.commentsCount=comments_count
        self.likesCount=likes_count

    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }


class ChapterOutSyncVersion(ChapterBase):
    id: Optional[str] =None
    hasRead:bool
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }

class ChapterUpdate(ChapterBase):
    bookId:Optional[str]=None
    number: Optional[int]=None
    id: Optional[str] =None
    dateUpdated: Optional[str]=None
    pageCount: Optional[int]=0
    pages: Optional[List[str]] = None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateUpdated']= now_str
        values['id']= str(values.get('_id'))
        return values
    
    
    
    
class ChapterUpdateStatusOrLabel(BaseModel):
    chapterLabel: Optional[str] = None
    status: Optional[str] = None
    dateUpdated: Optional[str] = datetime.now(timezone.utc).isoformat()  # This is a fixed value at class load time
    coverImage:Optional[str] = None

    def __init__(self, **kwargs):
        # If dateUpdated is not provided, set the current time
        if 'dateUpdated' not in kwargs:
            kwargs['dateUpdated'] = datetime.now(timezone.utc).isoformat()
        super().__init__(**kwargs)
        
class ChapterUpdateStatusOrLabelRequest(BaseModel):
    chapterLabel: Optional[str] = None
    status: Optional[str] = None
    dateUpdated: Optional[str] = datetime.now(timezone.utc).isoformat()  # This is a fixed value at class load time
    coverImage:Optional[str] = None

    def __init__(self, **kwargs):
        # If dateUpdated is not provided, set the current time
        if 'dateUpdated' not in kwargs:
            kwargs['dateUpdated'] = datetime.now(timezone.utc).isoformat()
        super().__init__(**kwargs)
        


class RecentChapterOut(ChapterOut):
    dateUpdated: Optional[str]=None
    wordCount: Optional[int]=0
