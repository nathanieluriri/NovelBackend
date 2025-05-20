from schemas.imports import *

class ClientData(BaseModel):
    ip:str
    city:str
    region:str
    country:str
    latitude:str
    longitude:str
    Network:str
    timezone:str

class VerificationRequest(BaseModel):
    otp: str
    access_token: str