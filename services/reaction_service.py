# ============================================================================
# REACTION SERVICE
# ============================================================================
# This file was auto-generated on: 2026-02-17 19:06:56 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.reaction import (
    create_reaction,
    get_reaction,
    get_reactions,
    update_reaction,
    delete_reaction,
)
from schemas.reaction import ReactionCreate, ReactionUpdate, ReactionOut


async def add_reaction(reaction_data: ReactionCreate) -> ReactionOut:
    """adds an entry of ReactionCreate to the database and returns an object

    Returns:
        _type_: ReactionOut
    """
    return await create_reaction(reaction_data)


async def remove_reaction_for_user(user_id: str, author_room_id: str) -> bool:
    """Delete a user's reaction within a specific author room."""
    existing = await get_reaction({"userId": user_id, "authorRoomId": author_room_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Reaction not found for user in this room")

    if not existing.id or not ObjectId.is_valid(existing.id):
        raise HTTPException(status_code=400, detail="Invalid reaction ID format")

    result = await delete_reaction({"_id": ObjectId(existing.id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reaction not found")
    return True
    
async def retrieve_reaction_by_user_and_room(user_id: str, author_room_id: str) -> ReactionOut:
    """Retrieves the reaction for a user in a specific author room."""
    result = await get_reaction({"userId": user_id, "authorRoomId": author_room_id})
    if not result:
        raise HTTPException(status_code=404, detail="Reaction not found for user in this room")
    return result


async def retrieve_reaction_by_room(author_room_id: str) -> ReactionOut:
    """Retrieves the reaction for a user in a specific author room."""
    result = await get_reaction({"authorRoomId": author_room_id})
    if not result:
        raise HTTPException(status_code=404, detail="Reaction not found for user in this room")
    return result


async def retrieve_reactions(start=0, stop=100) -> List[ReactionOut]:
    """Retrieves ReactionOut Objects in a list

    Returns:
        _type_: ReactionOut
    """
    return await get_reactions(start=start,stop=stop)


async def update_reaction_by_id(user_id: str, author_room_id: str, reaction_data: ReactionUpdate) -> ReactionOut:
    """Update a user's reaction in a specific author room.

    Looks up the existing reaction by `userId` and `authorRoomId`; if found,
    updates it with the supplied `reaction_data` (partial update). Raises 404
    when no reaction exists for the user/room, or 400 for invalid ObjectId.
    """

    existing = await get_reaction({"userId": user_id, "authorRoomId": author_room_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Reaction not found for user in this room")

    if not existing.id or not ObjectId.is_valid(existing.id):
        raise HTTPException(status_code=400, detail="Invalid reaction ID format")

    filter_dict = {"_id": ObjectId(existing.id)}
    result = await update_reaction(filter_dict, reaction_data)

    if not result:
        raise HTTPException(status_code=404, detail="Reaction not found or update failed")

    return result
