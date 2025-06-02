from schemas.imports import *


class ChapterBase(BaseModel):
    bookId:str
    number: Optional[int]=0
    chapterLabel:str
    status:str


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
    
    
class ChapterOut(ChapterBase):
    id: Optional[str] =None
    lastAccessed: Optional[str]=datetime.now(timezone.utc).isoformat()
    dateCreated: Optional[str]=None
    dateUpdated: Optional[str]=None
    pageCount: Optional[int]=0
    pages: Optional[List[str]] = None
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
    