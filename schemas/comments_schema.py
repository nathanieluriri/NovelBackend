from schemas.imports import *
from enum import Enum
from pydantic_async_validation import async_field_validator, AsyncValidationModelMixin, ValidationInfo
from core.database import db
class CommentType(str,Enum):
    reply_chapter="Reply To Chapter"
    reply_comment ="Reply To Comment"
    reply_reply ="Reply To Reply"

class CommentBaseRequest(BaseModel):
    chapterId: str
    text:str
    commentType:Optional[CommentType]=CommentType.reply_chapter
class UpdateCommentBaseRequest(BaseModel):
    commentId: str
    text:str


class CommentBase(BaseModel):
    userId:str
    role:str
    text:str
    chapterId: str
    commentType:Optional[CommentType]=CommentType.reply_chapter

class CommentCreate(CommentBase):
    userId:Optional[str]=None
    role:Optional[str]=None
    commentType:Optional[CommentType]=CommentType.reply_chapter
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    @model_validator(mode='before')
    def set_dates(cls,values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['dateCreated']= now_str
        return values

    
    
class CommentOut(AsyncValidationModelMixin,CommentBase):
    id: Optional[str] =None
    commentType:Optional[CommentType]=CommentType.reply_chapter
    dateCreated: Optional[str]=datetime.now(timezone.utc).isoformat()
    firstName:Optional[str]=None
    lastName:Optional[str]=None
    avatar:Optional[str]=None
    email:Optional[str]=None
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        try:
            if isinstance(values,dict):
                values['id']= str(values.get('_id'))
                return values
        except Exception as e:
            print("exception in comment out ",str(e))
    @async_field_validator('userId')
    async def set_user_details(self,config: ValidationInfo):
        users_collection = db.users
        user_id_string = self.userId
        query = {'_id': ObjectId(user_id_string)}
        projection = {
            'firstName': 1,
            'lastName': 1,
            'avatar': 1,
            'email':1,
            '_id': 0  # Exclude the _id from the result
        }
        user_details = await users_collection.find_one(query, projection)
        if user_details:
            print("User found:")
            print(user_details)
            self.firstName= user_details.get("firstName",None)
            self.lastName= user_details.get("lastName",None)
            self.avatar = user_details.get("avatar",None)
            self.email = user_details.get("email",None)
        return self

    model_config = {
        'populate_by_name': True,
        'arbitrary_types_allowed': True,
        'json_encoders':{ObjectId:str}
    }


