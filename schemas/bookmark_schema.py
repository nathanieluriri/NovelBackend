from schemas.imports import *

class BookMarkBase(BaseModel):
    userId:str
    pageId: str


class BookMarkCreate(BookMarkBase):
    dateCreated: Optional[str]=None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
    
class BookMarkOut(BookMarkBase):
    id: Optional[str] =None
    dateCreated: Optional[str]=None
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values
    

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }


