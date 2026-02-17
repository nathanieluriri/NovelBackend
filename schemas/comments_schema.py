from enum import Enum

from core.database import db
from pydantic_async_validation import AsyncValidationModelMixin, ValidationInfo, async_field_validator
from schemas.imports import *


class InteractionTargetType(str, Enum):
    book = "book"
    chapter = "chapter"
    page = "page"


class CommentType(str, Enum):
    reply_target = "reply_target"
    reply_chapter = "Reply To Chapter"
    reply_comment = "Reply To Comment"
    reply_reply = "Reply To Reply"


class CommentCreateRequest(BaseModel):
    text: str
    targetType: Optional[InteractionTargetType] = None
    targetId: Optional[str] = None
    chapterId: Optional[str] = None
    parentCommentId: Optional[str] = None
    commentType: Optional[CommentType] = CommentType.reply_target

    @model_validator(mode="before")
    def normalize_legacy_payload(cls, values):
        values = values or {}
        if values.get("targetType") is None and values.get("targetId") is None and values.get("chapterId") is not None:
            values["targetType"] = InteractionTargetType.chapter.value
            values["targetId"] = values.get("chapterId")
        return values

    @model_validator(mode="after")
    def validate_target_and_reply(self):
        if self.targetType is None or self.targetId is None:
            raise ValueError("targetType and targetId are required")
        if len(self.targetId) != 24:
            raise ValueError("targetId must be exactly 24 characters long")
        if self.parentCommentId is not None and len(self.parentCommentId) != 24:
            raise ValueError("parentCommentId must be exactly 24 characters long")
        if self.commentType in (CommentType.reply_comment, CommentType.reply_reply) and self.parentCommentId is None:
            raise ValueError("parentCommentId is required when commentType is reply_comment")
        if self.commentType in (CommentType.reply_target, CommentType.reply_chapter) and self.parentCommentId is not None:
            raise ValueError("parentCommentId must be empty when commentType is reply_target")
        return self


class CommentBaseRequest(BaseModel):
    chapterId: str
    text: str
    commentType: Optional[CommentType] = CommentType.reply_target


class UpdateCommentBaseRequest(BaseModel):
    commentId: str
    text: str


class CommentCreate(BaseModel):
    userId: str
    role: str
    text: str
    targetType: InteractionTargetType
    targetId: str
    parentCommentId: Optional[str] = None
    commentType: Optional[CommentType] = CommentType.reply_target
    dateCreated: Optional[str] = datetime.now(timezone.utc).isoformat()

    @model_validator(mode="before")
    def set_dates(cls, values):
        now_str = datetime.now(timezone.utc).isoformat()
        values["dateCreated"] = now_str
        return values


class CommentOut(AsyncValidationModelMixin, BaseModel):
    id: Optional[str] = None
    userId: str
    role: str
    text: str
    targetType: InteractionTargetType
    targetId: str
    parentCommentId: Optional[str] = None
    commentType: Optional[CommentType] = CommentType.reply_target
    dateCreated: Optional[str] = datetime.now(timezone.utc).isoformat()
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None

    @model_validator(mode="before")
    def set_dynamic_values(cls, values):
        if isinstance(values, dict):
            values["id"] = str(values.get("_id"))
            # Compatibility with old chapter-only comments.
            if values.get("targetType") is None and values.get("chapterId") is not None:
                values["targetType"] = InteractionTargetType.chapter.value
                values["targetId"] = values.get("chapterId")
        return values

    @async_field_validator("userId")
    async def set_user_details(self, config: ValidationInfo):
        user_details = await db.users.find_one(
            {"_id": ObjectId(self.userId)},
            {
                "firstName": 1,
                "lastName": 1,
                "avatar": 1,
                "email": 1,
                "_id": 0,
            },
        )
        if user_details:
            self.firstName = user_details.get("firstName")
            self.lastName = user_details.get("lastName")
            self.avatar = user_details.get("avatar")
            self.email = user_details.get("email")
        return self

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
