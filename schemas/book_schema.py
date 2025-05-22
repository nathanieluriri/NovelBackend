from pydantic import BaseModel, Field,model_validator
from schemas.chapter_schema import ChapterOut
from schemas.imports import *


class BookBase(BaseModel):
    name: str
    number:int


class BookCreate(BookBase):
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    dateUpdated: Optional[str]=None
    chapterCount: Optional[int]=0
    chapters: Optional[List[str]] = None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        values['dateUpdated']= now_str
        return values
    
    
class BookOut(BookCreate):
    id: Optional[str] =None
    lastAccessed: str
    @model_validator(mode='before')
    def set_values(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['lastAccessed']= now_str
        values['id']= str(values.get('_id'))
        return values
    
    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }


class BookUpdate(BaseModel):
    name: Optional[str] = None
    number: Optional[int] = None
    dateUpdated: Optional[str]=None
    chapterCount: Optional[int]=0
    chapters: Optional[List[str]] = None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateUpdated']= now_str
        return values