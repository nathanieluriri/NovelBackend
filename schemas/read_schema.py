from schemas.imports import *

class MarkAsRead(BaseModel):
    userId:str
    chapterId:str
    hasRead:bool