from schemas.imports import *

class ClientData(BaseModel):
    ip:str
    city:Optional[str]=None
    region:Optional[str]=None
    country:Optional[str]=None
    latitude:Optional[str]=None
    longitude:Optional[str]=None
    Network:Optional[str]=None
    timezone:Optional[str]=None
    dateTime:str
    clientType:str
    userId:str

class VerificationRequest(BaseModel):
    otp: str
    access_token: str