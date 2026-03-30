from schemas.imports import *
from security.hash import hash_password
from typing import Union
from enum import Enum
from core.database import db
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo
from schemas.chapter_schema import ChapterOut,ChapterOutSyncVersion
from schemas.bookmark_schema import BookMarkOut,   BookMarkOutSync
from schemas.likes_schema import LikeOut


def _normalize_auth_providers(values: Any) -> dict[str, Any]:
    if values is None:
        return {}

    normalized_values = dict(values)
    provider = normalized_values.get("provider")
    auth_providers = normalized_values.get("authProviders")
    normalized_providers: list[str] = []

    if isinstance(auth_providers, list):
        for item in auth_providers:
            if isinstance(item, Enum):
                item = item.value
            if isinstance(item, str):
                candidate = item.strip().lower()
                if candidate and candidate not in normalized_providers:
                    normalized_providers.append(candidate)

    if isinstance(provider, Enum):
        provider = provider.value
    if isinstance(provider, str):
        candidate = provider.strip().lower()
        if candidate and candidate not in normalized_providers:
            normalized_providers.append(candidate)

    if normalized_providers:
        normalized_values["authProviders"] = normalized_providers
    return normalized_values


class Stage(BaseModel):
    currentStage:Optional[int]=1
    currentExperience:Optional[int]=0
    
    
class ReadingHistory(BaseModel):
    chapterId:Optional[str]=None
    chapterNumber:Optional[int]=None
    chapterSnippet:Optional[str]=None


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
        return self
        
        
class NewUserCreate(AsyncValidationModelMixin,NewUserBase):
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    status:Optional[UserStatus]=UserStatus.ACTIVE
    avatar:Optional[str]=None
    password: Optional[Union[str ,bytes]]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    balance:Optional[int]=0
    unlockedChapters:Optional[List[str]]=Field(default_factory=list)
    googleAccessToken:Optional[str]=None
    authProviders: List[str] = Field(default_factory=list)
    subscription: Optional[SubscriptionInfo] = Field(default_factory=SubscriptionInfo)
    
    @async_field_validator('unlockedChapters')
    async def set_default_chapter(self,config: ValidationInfo):
        chapter = await get_chapter_one_id()
        if chapter.id not in self.unlockedChapters:
            self.unlockedChapters.append(chapter.id)
        
    @model_validator(mode='before')
    def set_dates(cls,values):
        values = _normalize_auth_providers(values)
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    @model_validator(mode='after')
    def obscure_password(self):
        if self.provider=="credentials" and self.password is not None:
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
    stopped_reading:Optional[ReadingHistory] = None
    authProviders: List[str] = Field(default_factory=list)
    subscription: Optional[SubscriptionInfo] = Field(default_factory=SubscriptionInfo)

    @model_validator(mode='before')
    def set_auth_providers(cls, values):
        return _normalize_auth_providers(values)

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
    
    stopped_reading:Optional[ReadingHistory] = None
    authProviders: List[str] = Field(default_factory=list)
    subscription: Optional[SubscriptionInfo] = Field(default_factory=SubscriptionInfo)
    @model_validator(mode='before')
    def set_id(cls,values):
        values = _normalize_auth_providers(values)
        if values.get('_id') is not None:
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

    @model_validator(mode='after')
    def check_login_credentials(self):
        if self.provider=="credentials" and self.password is None:
            raise ValueError("Password is compulsory for credentials provider")
        return self

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
        values = _normalize_auth_providers(values)
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
    
    
