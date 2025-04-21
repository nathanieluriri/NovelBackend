from schemas.imports import *


class accessTokenBase(BaseModel):
    userId:str

    
class accessTokenCreate(accessTokenBase):
    dateCreated:Optional[str]=None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values

    
class accessTokenOut(accessTokenCreate):
    accesstoken: Optional[str] =None
    @model_validator(mode='before')
    def set_values(cls,values):
        if values is None:
            values = {}
        values['accesstoken']= str(values.get('_id'))
        return values
    
    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }
    
    
    

    

class refreshTokenBase(BaseModel):
    userId:str
    previousAccessToken:str

    
class refreshTokenCreate(refreshTokenBase):
    dateCreated:Optional[str]=None
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values

    
class refreshTokenOut(refreshTokenCreate):
    refreshtoken: Optional[str] =None
    @model_validator(mode='before')
    def set_values(cls,values):
        if values is None:
            values = {}
        values['refreshtoken']= str(values.get('_id'))
        return values
    
    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
    }


class TokenOut(refreshTokenOut,accessTokenOut):
    pass



class refreshTokenRequest(BaseModel):
    refreshToken:str