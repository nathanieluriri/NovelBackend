from schemas.imports import *
from schemas.utils import clean_html


class PageBase(BaseModel):
    chapterId:str
    number: int
    textContent:str
    status:str
    
class PageUpdateRequest(BaseModel):
    textContent:str

class PageCreate(PageBase):
    dateCreated: Optional[str]=None
    dateUpdated: Optional[str]=None
    textCount: Optional[int]=0

    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        values['dateUpdated']= now_str
        return values
    @model_validator(mode='after')
    def set_count(self):
        cleaned = clean_html(self.textContent)
        self.textCount=len(cleaned.split())
        return self
    
class PageOut(PageCreate):
    id: Optional[str] =None
    lastAccessed: Optional[str] =None
    @model_validator(mode='before')
    def set_values(cls,values):
        if values is None:
            values = {}
        now_str = datetime.now(timezone.utc).isoformat()
        values['lastAccessed']= now_str
        values['id']= str(values.get('_id'))
        return values
    
    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }

class PageUpdate(BaseModel):
    textContent:str
    dateUpdated: Optional[str]=None
    textCount: Optional[int]=0
    @model_validator(mode='before')
    def set_updated_date(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateUpdated']= now_str
        return values
    @model_validator(mode='after')
    def set_text_count(self):
        cleaned = clean_html(self.textContent)
        self.textCount=len(cleaned.split())
        return self
