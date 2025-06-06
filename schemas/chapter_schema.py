from schemas.imports import *
from fastapi import Form

class ChapterBase(BaseModel):
    bookId:str
    number: Optional[int]=0
    chapterLabel:str
    status:str
    @classmethod
    def as_form(
        cls,
        bookId: str = Form(...),
        chapterLabel: str = Form(...),
        status: str = Form(...)
    ) -> "ChapterBase":
        return cls(bookId=bookId, chapterLabel=chapterLabel, status=status)
class ChapterCreate(ChapterBase):
    coverImage: Optional[str]=None
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
    coverImage: Optional[str]=None
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
    
    
    
    
class ChapterUpdateStatusOrLabel(BaseModel):
    chapterLabel: Optional[str] = None
    status: Optional[str] = None
    dateUpdated: Optional[str] = datetime.now(timezone.utc).isoformat()  # This is a fixed value at class load time
    coverImage:Optional[str] = None
    # Better solution: make it callable so it generates a fresh timestamp each time
    dateUpdated: Optional[str] = None  # Remove the default value from here

    def __init__(self, **kwargs):
        # If dateUpdated is not provided, set the current time
        if 'dateUpdated' not in kwargs:
            kwargs['dateUpdated'] = datetime.now(timezone.utc).isoformat()
        super().__init__(**kwargs)
        
    @classmethod
    def as_form(
        cls,
        chapterLabel: Optional[str] = Form(...),
        status: Optional[str] = Form(...)
    ) -> "ChapterBase":
        return cls(chapterLabel=chapterLabel, status=status)