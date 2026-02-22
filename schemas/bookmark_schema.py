from enum import Enum

from schemas.imports import *
from schemas.cache_summary_schema import ChapterSummaryOut


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
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values

        normalized = dict(values)
        if (
            normalized.get("targetType") is None
            and normalized.get("targetId") is None
            and normalized.get("pageId") is not None
        ):
            normalized["targetType"] = InteractionTargetType.page.value
            normalized["targetId"] = normalized.get("pageId")
        return normalized

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
    dateCreated: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    def set_dates(cls, values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values

        normalized = dict(values)
        if normalized.get("dateCreated") is None:
            normalized["dateCreated"] = datetime.now(timezone.utc).isoformat()
        return normalized


class BookMarkOut(BookMarkCreate):
    id: Optional[str] = None
    pageNumber: Optional[int] = None
    chapterSummary: Optional[ChapterSummaryOut] = None

    @model_validator(mode="before")
    def set_dynamic_values(cls, values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if isinstance(values, dict):
            normalized = dict(values)
            if normalized.get("id") is None and normalized.get("_id") is not None:
                normalized["id"] = str(normalized.get("_id"))
            # Compatibility with legacy page-only bookmark docs.
            if normalized.get("targetType") is None and normalized.get("pageId") is not None:
                normalized["targetType"] = InteractionTargetType.page.value
                normalized["targetId"] = normalized.get("pageId")
            return normalized
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
