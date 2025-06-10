from schemas.imports import *
from security.hash import hash_password
from typing import Union
from schemas.user_schema import UserOut
from schemas.chapter_schema import RecentChapterOut
from enum import Enum

class ChangeType(str, Enum):
    increase = "increase"
    decrease = "decrease"
    no_change = "no change"

class AdminBase(BaseModel):
    email: EmailStr
    password:  str 
    
      
class AllowedAdminCreate(BaseModel):
    email:EmailStr
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    invitedBy:EmailStr
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
class DefaultAllowedAdminCreate(BaseModel):
    email:EmailStr
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
class NewAdminCreate(AdminBase):
    firstName:Optional[str]
    lastName:Optional[str]
    avatar:Optional[str]=None
    password: Union[str ,bytes]
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()

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
    email:EmailStr
    invitedBy:Optional[EmailStr]=None
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





class AdminUpdate(BaseModel):
    firstName:Optional[str] =None
    lastName:Optional[str] =None
    avatar:Optional[str] =None

class ChapterAnalytics(BaseModel):
    totalChapters: Optional[str] = None
    chapterChange: Optional[str] = None
    changeType: Optional[ChangeType] = None

class PageAnalytics(BaseModel):
    totalpages: Optional[str] = None
    pageChange: Optional[str] = None
    changeType: Optional[ChangeType] = None

class ReaderAnalytics(BaseModel):
    totalReaders: Optional[str] = None
    readerChange: Optional[str] = None
    changeType: Optional[ChangeType] = None

class RevenueAnalytics(BaseModel):
    totalRevenue:Optional[str] =None
    revenueChange:Optional[str] =None
    changeType: Optional[ChangeType] = None


class AdminDashboardAnalytics(BaseModel):
    chapterAnalytics:ChapterAnalytics
    pageAnalytics:PageAnalytics
    readerAnalytics:ReaderAnalytics
    revenueAnalytics:RevenueAnalytics
    recentChapters: List[RecentChapterOut]
    recentUsers:List[UserOut]
    
