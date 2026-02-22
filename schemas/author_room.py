# ============================================================================
#AUTHOR_ROOM SCHEMA 
# ============================================================================
# This file was auto-generated on: 2026-02-17 12:26:24 WAT
# It contains Pydantic classes  database
# for managing attributes and validation of data in and out of the MongoDB database.
#
# ============================================================================

from schemas.imports import *
from pydantic import AliasChoices, Field
import time
from schemas.utils import normalize_datetime_to_iso



class AuthorRoomBase(BaseModel):
    # Add other fields here
    text:str
    chapterId:str 
    pass

class AuthorRoomCreate(AuthorRoomBase):
    # Add other fields here 
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class AuthorRoomUpdate(BaseModel):
    # Add other fields here
    text:str
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class AuthorRoomOut(AuthorRoomBase):
    # Add other fields here 
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    date_created: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("date_created", "dateCreated"),
        serialization_alias="dateCreated",
    )
    last_updated: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("last_updated", "lastUpdated"),
        serialization_alias="lastUpdated",
    )
    
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if isinstance(values, BaseModel):
            values = values.model_dump()
        if not isinstance(values, dict):
            return values
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])  # coerce to string before validation
        date_created = values.get("date_created", values.get("dateCreated"))
        if date_created is not None:
            values["date_created"] = normalize_datetime_to_iso(date_created)
        last_updated = values.get("last_updated", values.get("lastUpdated"))
        if last_updated is not None:
            values["last_updated"] = normalize_datetime_to_iso(last_updated)
        return values
            
    class Config:
        populate_by_name = True  # allows using `id` when constructing the model
        arbitrary_types_allowed = True  # allows ObjectId type
        json_encoders ={
            ObjectId: str  # automatically converts ObjectId → str
        }
