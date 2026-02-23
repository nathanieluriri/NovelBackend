from schemas.imports import *
from security.hash import hash_password
from typing import Union
from enum import Enum
from core.database import db
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo
from schemas.chapter_schema import ChapterOut,ChapterOutSyncVersion
from schemas.bookmark_schema import BookMarkOut,   BookMarkOutSync
from schemas.likes_schema import LikeOut
class Stage(BaseModel):
    currentStage:Optional[int]=1
    currentExperience:Optional[int]=0
    
    
class ReadingHistory(BaseModel):
    chapterId:Optional[str]="6843840255b3388477dcdaed"
    chapterNumber:Optional[int]=1
    chapterSnippet:Optional[str]= "Not every relative celebrated when my parents decided to marry. Their vows were blessed in a small church but not with joy. Maybe people had already seen my father’s empty wallet before my mother did. Maybe they thought love was too expensive for the poor."


class SubscriptionInfo(BaseModel):
    active: Optional[bool] = False
    expiresAt: Optional[str] = None
    
    
    
async def get_chapter_one_id():
    chapter = await db.chapters.find_one({"number":1})
    chapterOut = ChapterOut(**chapter)
    return chapterOut
class Provider(str, Enum):
    CREDENTIALS = "credentials"
    GOOGLE = "google"
    
    
class UserStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    SUSPENDED = "Suspended"

class NewUserBase(BaseModel):
    provider:Provider
    email: EmailStr
    password:  Optional[str]=None 
    googleAccessToken:Optional[str]=None
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    @model_validator(mode='after')
    def check_password_and_credentials(self):
        if self.provider=="credentials" and self.password==None:
            raise ValueError("Password is compulsory for credentials provider")
        elif self.provider=="google" and self.googleAccessToken==None:
            raise ValueError("Google access token is compulsory for google provider")
        return self
        
        
class NewUserCreate(AsyncValidationModelMixin,NewUserBase):
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    status:Optional[UserStatus]=UserStatus.ACTIVE
    avatar:Optional[str]=None
    password: Union[str ,bytes]
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    balance:Optional[int]=0
    unlockedChapters:Optional[List[str]]=Field(default_factory=list)
    googleAccessToken:Optional[str]=None
    subscription: Optional[SubscriptionInfo] = Field(default_factory=SubscriptionInfo)
    
    @async_field_validator('unlockedChapters')
    async def set_default_chapter(self,config: ValidationInfo):
        chapter = await get_chapter_one_id()
        self.unlockedChapters.append(chapter.id)
        
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
    email:str
    balance:Optional[int]=None
    accessToken: Optional[str]=None
    refreshToken:Optional[str]=None
    unlockedChapters:Optional[List[str]]=Field(default_factory=list)
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat() 
    stage: Optional[Stage] = Field(default_factory=Stage)
    bookmarks:Optional[List[BookMarkOutSync]]=Field(default_factory=list)
    likes:Optional[List[LikeOut]] = Field(default_factory=list)
    stopped_reading:Optional[ReadingHistory] = Field(default_factory=ReadingHistory)
    subscription: Optional[SubscriptionInfo] = Field(default_factory=SubscriptionInfo)
class UserOut(BaseModel):
    userId: Optional[str] =None
    status:Optional[UserStatus]=None
    email:str
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    accessToken: Optional[str]=None
    refreshToken:Optional[str]=None
    balance:Optional[int]=0
    unlockedChapters:Optional[List[str]]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat() 
    stage:Optional[Stage]=Field(default_factory=Stage)
    bookmarks:Optional[List[BookMarkOutSync]]=Field(default_factory=list)
    likes:Optional[List[LikeOut]] = Field(default_factory=list)
    
    stopped_reading:Optional[ReadingHistory] = Field(default_factory=ReadingHistory)
    subscription: Optional[SubscriptionInfo] = Field(default_factory=SubscriptionInfo)
    @model_validator(mode='before')
    def set_id(cls,values):
        values['userId'] = str(values['_id'])
        return values
    
        

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }


class UserOutChapterDetails(UserOut):
    chapterDetails:List[ChapterOutSyncVersion]


class OldUserBase(BaseModel):
    provider:Provider
    email: EmailStr
    password: Optional[str]=None
    googleAccessToken:Optional[str]=None

class OldUserCreate(OldUserBase):
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()

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
        values['userId']= str(values['_id'])
        return values
        

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }



class UserUpdate(BaseModel):
    firstName:Optional[str] =None
    lastName:Optional[str] =None
    avatar:Optional[str] =None
    status:Optional[UserStatus]=None
    
class UserStatusUpdate(BaseModel):
    firstName:Optional[str] =None
    lastName:Optional[str] =None
    avatar:Optional[str] =None
    status:Optional[UserStatus]=None
    
    
