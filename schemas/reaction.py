# ============================================================================
#REACTION SCHEMA 
# ============================================================================
# This file was auto-generated on: 2026-02-17 19:06:38 WAT
# It contains Pydantic classes  database
# for managing attributes and validation of data in and out of the MongoDB database.
#
# ============================================================================

from schemas.imports import *
from pydantic import AliasChoices, Field
import time
from schemas.utils import normalize_datetime_to_iso


class ReactionBase(BaseModel):
    reaction:str
    authorRoomId:str

    @model_validator(mode="before")
    @classmethod
    def normalize_reaction(cls, values):
        if not isinstance(values, dict):
            return values
        reaction = values.get("reaction")
        if reaction is None:
            return values
        if not isinstance(reaction, str):
            return values
        normalized_reaction = reaction.strip()
        if not normalized_reaction:
            raise ValueError("reaction must not be empty")
        values["reaction"] = normalized_reaction
        return values

class ReactionCreate(ReactionBase):
    # Add other fields here
    userId:str 
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class ReactionUpdate(BaseModel):
    reaction: Optional[str] = None
    last_updated: int = Field(default_factory=lambda: int(time.time()))

    @model_validator(mode="before")
    @classmethod
    def normalize_reaction(cls, values):
        if not isinstance(values, dict):
            return values
        reaction = values.get("reaction")
        if reaction is None:
            return values
        if not isinstance(reaction, str):
            return values
        normalized_reaction = reaction.strip()
        if not normalized_reaction:
            raise ValueError("reaction must not be empty")
        values["reaction"] = normalized_reaction
        return values

class ReactionOut(ReactionBase):
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
            
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
