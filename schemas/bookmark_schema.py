from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo
from schemas.imports import *
from services.page_services import fetch_page

class BookMarkBase(BaseModel):
    userId:str
    pageId: str


class BookMarkCreate(BookMarkBase):
    chapterLabel:str
    chapterId:str
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
    
class BookMarkOut(BookMarkCreate):
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





class BookMarkOutAsync(AsyncValidationModelMixin,BookMarkCreate):
    id: Optional[str] =None
    pageNumber:Optional[int]=None 
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @async_field_validator('pageNumber')
    async def set_page_number(self,config: ValidationInfo):
        # Comments Count
        pages = await fetch_page(chapterId=self.chapterId)
        pageNumber = 1
        
        for page in pages:
            if page.id == self.pageId:
                self.pageNumber=pageNumber
                break
            pageNumber += 1  
         
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }