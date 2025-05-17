from schemas.imports import *
from security.hash import hash_password
from typing import Union

class NewAdminBase(BaseModel):
    email: EmailStr
    password:  str 
    
      
class NewAdminCreate(NewAdminBase):
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    password: Union[str ,bytes]
    dateCreated:Optional[str]=None

    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    @model_validator(mode='after')
    def obscure_password(self):
        self.password=hash_password(self.password)
        return self

class NewAdminOut(BaseModel):
    userId: Optional[str] =None
    accessToken: Optional[str]=None
    refreshToken:Optional[str]=None
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    dateCreated:Optional[str]=None 
    @model_validator(mode='before')
    def set_values(cls,values):
        values['userId']= str(values.get('_id'))
        return values
        

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }


