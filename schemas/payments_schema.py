from schemas.imports import *
from enum import Enum

class TransactionType(str, Enum):
    real_cash = "cash"
    star_currency_transfer = "transfer of Star currency between accounts"
    chapter_purchase ="transfer of Star currency for chapter access"

# Records Transactions...
class TransactionIn(BaseModel):
    userId:str
    numberOfStars:Optional[int]=None
    TransactionType:TransactionType
    amount:Optional[int]=None
    dateCreated:Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values
    
class TransactionOut(BaseModel):
    id:str
    userId:str
    paymentId:str
    numberOfStars:int
    TransactionType:TransactionType
    amount:int
    dateCreated:str
    @model_validator(mode='before')
    def set_id(cls,values):
        values['id'] = str(values.get('_id'))
        return values    

    
class PaymentBundles(BaseModel):
    amount:int
    numberOfstars:int
    
class PaymentLink(BaseModel):
    userId:str 
    email:str 
    amount:str
    firstName:str
    lastName:str
    
class PaymentBundlesUpdate(BaseModel):
    amount:Optional[int]=None
    numberOfstars:Optional[int]=None
    
class PaymentBundlesOut(BaseModel):
    id:str
    amount:int
    numberOfstars:int
    @model_validator(mode='before')
    def set_id(cls,values):
        values['id'] = str(values.get('_id'))
        return values
    
    