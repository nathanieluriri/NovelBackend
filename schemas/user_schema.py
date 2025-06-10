from schemas.imports import *
from security.hash import hash_password
from typing import Union
from enum import Enum

class Provider(str, Enum):
    CREDENTIALS = "credentials"
    GOOGLE = "google"
    

class NewUserBase(BaseModel):
    provider:Provider
    email: EmailStr
    password:  str 
    googleAccessToken:Optional[str]=None
    
      
        
        
class NewUserCreate(NewUserBase):
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    password: Union[str ,bytes]
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    subscriptionStartDate:Optional[str]="None"
    subscriptionEndDate:Optional[str]="None"
    googleAccessToken:None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    @model_validator(mode='after')
    def obscure_password(self):
        if self.provider=="credentials":
            self.password=hash_password(self.password)
            return self

class NewUserOut(BaseModel):
    userId: Optional[str] =None
    accessToken: Optional[str]=None
    refreshToken:Optional[str]=None
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat() 
    @model_validator(mode='before')
    def set_values(cls,values):
        values['userId']= str(values.get('_id'))
        return values
        

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }


class UserOut(BaseModel):
    userId: Optional[str] =None
    email:Optional[EmailStr]=None
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat() 
    @model_validator(mode='before')
    def set_values(cls,values):
        values['userId']= str(values.get('_id'))
        return values
        

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }



class OldUserBase(BaseModel):
    provider:Provider
    email: EmailStr
    password: Optional[str]=None
    accessToken:Optional[str]=None

class OldUserCreate(OldUserBase):
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    subscriptionStartDate:Optional[str]=None
    subscriptionEndDate:Optional[str]=None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
    

class OldUserOut(NewUserOut):
    userId: Optional[str] =None
    accessToken: str
    refreshToken:str    
    @model_validator(mode='before')
    def set_values(cls,values):   
        values['userId']= str(values.get('_id'))
        return values
        

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }



class UserUpdate(BaseModel):
    firstName:Optional[str] =None
    lastName:Optional[str] =None
    avatar:Optional[str] =None
    provider:Optional[Provider] =None