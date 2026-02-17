from schemas.imports import *
from core.database import db
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo
from enum import Enum


class ChapterAccessType(str, Enum):
    free = "free"
    subscription = "subscription"
    paid = "paid"


LEGACY_STATUS_TO_ACCESS = {
    "free": ChapterAccessType.free.value,
    "subscription": ChapterAccessType.subscription.value,
    "paid": ChapterAccessType.paid.value,
    "premium": ChapterAccessType.paid.value,
    "locked": ChapterAccessType.paid.value,
}

class ChapterBaseRequest(BaseModel):
    bookId:str
    chapterLabel:str
    status: Optional[str]=None
    accessType: Optional[ChapterAccessType]=None
    unlockBundleId: Optional[str]=None
    coverImage: Optional[str]=None
    
    @model_validator(mode='before')
    def normalize_access_values(cls, values):
        values = values or {}
        access = values.get("accessType")
        legacy_status = values.get("status")
        if access is None and legacy_status is not None:
            mapped = LEGACY_STATUS_TO_ACCESS.get(str(legacy_status).strip().lower())
            values["accessType"] = mapped if mapped else ChapterAccessType.free.value
        elif access is None:
            values["accessType"] = ChapterAccessType.free.value
        return values
    
    @model_validator(mode='after')
    def validate_bundle_rules(self):
        if self.accessType == ChapterAccessType.paid and not self.unlockBundleId:
            raise ValueError("unlockBundleId is required when accessType is paid")
        if self.accessType in (ChapterAccessType.free, ChapterAccessType.subscription) and self.unlockBundleId is not None:
            raise ValueError("unlockBundleId must be empty unless accessType is paid")
        return self
    
class ChapterBase(ChapterBaseRequest):
    number: Optional[int]=0
    chapterLabel:Optional[str]=None
    status:Optional[str]=None
    accessType: Optional[ChapterAccessType]=ChapterAccessType.free
    unlockBundleId: Optional[str]=None
    
    
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
            # The ID is already set by the @model_validator(mode='before'), so we can use self.id
        chapter_id = self.id
        
        # Aggregate to get BOTH the count and the list of IDs in a single query
        page_data = await db.pages.aggregate([
            # Stage 1: Filter pages for the specific chapter
            {"$match": {"chapterId": chapter_id}},
            
            # Stage 2: Group all pages into a single document to calculate metrics
            {"$group": {
                "_id": None, # Group all documents into one
                "totalCount": {"$sum": 1},
                # Collect the page's _id (which is its unique identifier) into an array
                "pageIds": {"$push": "$_id"} 
            }},
            
            # Stage 3: Project and convert the _id ObjectIds to strings
            {"$project": {
                "_id": 0,
                "totalCount": 1,
                # Use $map to convert each ObjectId to a string before output
                "pageIds": {
                    "$map": {
                        "input": "$pageIds",
                        "as": "page_id",
                        "in": {"$toString": "$$page_id"}
                    }
                }
            }}
        ]).to_list(length=1)

        # Extract the data. If no pages are found, page_data will be empty.
        if page_data:
            data = page_data[0]
            self.pageCount = data.get("totalCount", 0)
            self.pages = data.get("pageIds", [])
        else:
            self.pageCount = 0
            self.pages = []



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
    accessType: Optional[ChapterAccessType] = None
    unlockBundleId: Optional[str] = None
    dateUpdated: Optional[str] = datetime.now(timezone.utc).isoformat()  # This is a fixed value at class load time
    coverImage:Optional[str] = None

    def __init__(self, **kwargs):
        # If dateUpdated is not provided, set the current time
        if 'dateUpdated' not in kwargs:
            kwargs['dateUpdated'] = datetime.now(timezone.utc).isoformat()
        super().__init__(**kwargs)
        
    @model_validator(mode='before')
    def normalize_access_values(cls, values):
        values = values or {}
        access = values.get("accessType")
        legacy_status = values.get("status")
        if access is None and legacy_status is not None:
            mapped = LEGACY_STATUS_TO_ACCESS.get(str(legacy_status).strip().lower())
            values["accessType"] = mapped if mapped else ChapterAccessType.free.value
        return values
    
    @model_validator(mode='after')
    def validate_bundle_rules(self):
        if self.accessType == ChapterAccessType.paid and not self.unlockBundleId:
            raise ValueError("unlockBundleId is required when accessType is paid")
        if self.accessType in (ChapterAccessType.free, ChapterAccessType.subscription) and self.unlockBundleId is not None:
            raise ValueError("unlockBundleId must be empty unless accessType is paid")
        return self
        
class ChapterUpdateStatusOrLabelRequest(BaseModel):
    chapterLabel: Optional[str] = None
    status: Optional[str] = None
    accessType: Optional[ChapterAccessType] = None
    unlockBundleId: Optional[str] = None
    dateUpdated: Optional[str] = datetime.now(timezone.utc).isoformat()  # This is a fixed value at class load time
    coverImage:Optional[str] = None

    def __init__(self, **kwargs):
        # If dateUpdated is not provided, set the current time
        if 'dateUpdated' not in kwargs:
            kwargs['dateUpdated'] = datetime.now(timezone.utc).isoformat()
        super().__init__(**kwargs)
        
    @model_validator(mode='before')
    def normalize_access_values(cls, values):
        values = values or {}
        access = values.get("accessType")
        legacy_status = values.get("status")
        if access is None and legacy_status is not None:
            mapped = LEGACY_STATUS_TO_ACCESS.get(str(legacy_status).strip().lower())
            values["accessType"] = mapped if mapped else ChapterAccessType.free.value
        return values
    
    @model_validator(mode='after')
    def validate_bundle_rules(self):
        if self.accessType == ChapterAccessType.paid and not self.unlockBundleId:
            raise ValueError("unlockBundleId is required when accessType is paid")
        if self.accessType in (ChapterAccessType.free, ChapterAccessType.subscription) and self.unlockBundleId is not None:
            raise ValueError("unlockBundleId must be empty unless accessType is paid")
        return self
        


class RecentChapterOut(ChapterOut):
    dateUpdated: Optional[str]=None
    wordCount: Optional[int]=0
