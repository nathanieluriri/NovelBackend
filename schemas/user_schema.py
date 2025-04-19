from schemas.imports import *

class UserBase(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserBase):
    DateJoined:Optional[str]=None
    SubscriptionStartDate:Optional[str]=None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        values['dateUpdated']= now_str
        return values
    
    

class UserOut(UserCreate):
    id: Optional[str] =None
    lastAccessed: str
    email:EmailStr
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
