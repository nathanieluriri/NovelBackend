from enum import Enum

from schemas.imports import *


class InteractionTargetType(str, Enum):
    book = "book"
    chapter = "chapter"
    page = "page"


class BookMarkCreateRequest(BaseModel):
    targetType: Optional[InteractionTargetType] = None
    targetId: Optional[str] = None
    pageId: Optional[str] = None

    @model_validator(mode="before")
    def normalize_legacy_payload(cls, values):
        values = values or {}
        if values.get("targetType") is None and values.get("targetId") is None and values.get("pageId") is not None:
            values["targetType"] = InteractionTargetType.page.value
            values["targetId"] = values.get("pageId")
        return values

    @model_validator(mode="after")
    def validate_target(self):
        if self.targetType is None or self.targetId is None:
            raise ValueError("targetType and targetId are required")
        if len(self.targetId) != 24:
            raise ValueError("targetId must be exactly 24 characters long")
        return self


class BookMarkBase(BaseModel):
    userId: str
    targetType: InteractionTargetType
    targetId: str


class BookMarkCreate(BookMarkBase):
    chapterLabel: Optional[str] = None
    chapterId: Optional[str] = None
    pageId: Optional[str] = None
    dateCreated: Optional[str] = datetime.now(timezone.utc).isoformat()

    @model_validator(mode="before")
    def set_dates(cls, values):
        now_str = datetime.now(timezone.utc).isoformat()
        values["dateCreated"] = now_str
        return values


class BookMarkOut(BookMarkCreate):
    id: Optional[str] = None
    pageNumber: Optional[int] = None

    @model_validator(mode="before")
    def set_dynamic_values(cls, values):
        if isinstance(values, dict):
            values["id"] = str(values.get("_id"))
            # Compatibility with legacy page-only bookmark docs.
            if values.get("targetType") is None and values.get("pageId") is not None:
                values["targetType"] = InteractionTargetType.page.value
                values["targetId"] = values.get("pageId")
        return values

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class BookMarkOutSync(BookMarkOut):
    pass


class BookMarkOutAsync(BookMarkOut):
    pass
