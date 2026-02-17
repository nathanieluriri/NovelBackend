from schemas.imports import *
from enum import Enum


class EntitlementGrantType(str, Enum):
    chapter_unlock = "chapter_unlock"


class EntitlementBase(BaseModel):
    userId: str
    chapterId: str
    grantType: EntitlementGrantType = EntitlementGrantType.chapter_unlock
    source: Optional[str] = None
    txRef: Optional[str] = None


class EntitlementCreate(EntitlementBase):
    createdAt: Optional[str] = datetime.now(timezone.utc).isoformat()

    @model_validator(mode='before')
    def set_dates(cls, values):
        now_str = datetime.now(timezone.utc).isoformat()
        values['createdAt'] = now_str
        return values


class EntitlementOut(EntitlementBase):
    id: Optional[str] = None
    createdAt: Optional[str] = None

    @model_validator(mode='before')
    def set_id(cls, values):
        values['id'] = str(values.get('_id'))
        return values
