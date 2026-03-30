from schemas.imports import *
from schemas.utils import normalize_datetime_to_iso


class GoogleOAuthExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def strip_code(self):
        self.code = self.code.strip()
        if not self.code:
            raise ValueError("Google OAuth code is required")
        return self


class GoogleOAuthExchangeRecordCreate(BaseModel):
    codeHash: str
    userId: str
    targetAlias: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiresAt: datetime
    consumedAt: Optional[datetime] = None


class GoogleOAuthExchangeRecord(BaseModel):
    id: Optional[str] = None
    codeHash: str
    userId: str
    targetAlias: str
    createdAt: Optional[str] = None
    expiresAt: Optional[str] = None
    consumedAt: Optional[str] = None

    @model_validator(mode="before")
    def set_values(cls, values):
        if values is None:
            values = {}
        values = dict(values)
        if values.get("_id") is not None:
            values["id"] = str(values["_id"])
        values["createdAt"] = normalize_datetime_to_iso(values.get("createdAt"))
        values["expiresAt"] = normalize_datetime_to_iso(values.get("expiresAt"))
        values["consumedAt"] = normalize_datetime_to_iso(values.get("consumedAt"))
        return values
