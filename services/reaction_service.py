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

from repositories.author_room import get_author_room
from repositories.chapter_repo import get_chapter_by_chapter_id
from repositories.reaction import (
    count_reactions,
    create_reaction,
    get_reaction,
    get_reaction_by_user_and_room,
    get_reactions,
    update_reaction,
    delete_reaction,
)
from repositories.user_repo import get_user_by_userId
from schemas.chapter_schema import ChapterOut
from schemas.reaction import ReactionCreate, ReactionUpdate, ReactionOut
from schemas.user_schema import UserOut
from services.access_service import has_chapter_access


async def _get_member_user_or_401(user_id: str) -> UserOut:
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=401, detail="Invalid token")

    user_doc = await get_user_by_userId(userId=user_id)
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid token")

    return UserOut(**user_doc)


async def _get_author_room_or_404(author_room_id: str):
    if not ObjectId.is_valid(author_room_id):
        raise HTTPException(status_code=400, detail="Invalid author_room ID format")

    author_room = await get_author_room({"_id": ObjectId(author_room_id)})
    if not author_room:
        raise HTTPException(status_code=404, detail="AuthorRoom not found")

    return author_room


async def _ensure_reaction_access(user_id: str, author_room_id: str) -> None:
    author_room = await _get_author_room_or_404(author_room_id=author_room_id)
    chapter = await get_chapter_by_chapter_id(chapterId=author_room.chapterId)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    user = await _get_member_user_or_401(user_id=user_id)
    chapter_out = ChapterOut(**chapter)
    await chapter_out.model_async_validate()

    can_access = await has_chapter_access(user=user, chapter=chapter_out)
    if not can_access:
        raise HTTPException(status_code=403, detail="You do not have access to react to this chapter")


async def add_reaction(reaction_data: ReactionCreate) -> ReactionOut:
    """adds an entry of ReactionCreate to the database and returns an object.

    If the user has already reacted to the author room, the existing reaction
    is replaced with the new value instead of returning a conflict.

    Returns:
        _type_: ReactionOut
    """
    await _ensure_reaction_access(
        user_id=reaction_data.userId,
        author_room_id=reaction_data.authorRoomId,
    )
    existing = await get_reaction_by_user_and_room(
        user_id=reaction_data.userId,
        author_room_id=reaction_data.authorRoomId,
    )
    if existing:
        if not existing.id or not ObjectId.is_valid(existing.id):
            raise HTTPException(status_code=400, detail="Invalid reaction ID format")
        return await update_reaction(
            {"_id": ObjectId(existing.id)},
            ReactionUpdate(reaction=reaction_data.reaction),
        )
    return await create_reaction(reaction_data)


async def remove_reaction_for_user(user_id: str, author_room_id: str) -> bool:
    """Delete a user's reaction within a specific author room."""
    await _ensure_reaction_access(user_id=user_id, author_room_id=author_room_id)
    existing = await get_reaction_by_user_and_room(user_id=user_id, author_room_id=author_room_id)
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
    result = await get_reaction_by_user_and_room(user_id=user_id, author_room_id=author_room_id)
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


async def retrieve_reactions_count() -> int:
    return await count_reactions()


async def update_reaction_by_id(user_id: str, author_room_id: str, reaction_data: ReactionUpdate) -> ReactionOut:
    """Update a user's reaction in a specific author room.

    Looks up the existing reaction by `userId` and `authorRoomId`; if found,
    updates it with the supplied `reaction_data` (partial update). Raises 404
    when no reaction exists for the user/room, or 400 for invalid ObjectId.
    """

    if reaction_data.reaction is None:
        raise HTTPException(status_code=400, detail="reaction is required")

    await _ensure_reaction_access(user_id=user_id, author_room_id=author_room_id)
    existing = await get_reaction_by_user_and_room(user_id=user_id, author_room_id=author_room_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Reaction not found for user in this room")

    if not existing.id or not ObjectId.is_valid(existing.id):
        raise HTTPException(status_code=400, detail="Invalid reaction ID format")

    filter_dict = {"_id": ObjectId(existing.id)}
    result = await update_reaction(filter_dict, reaction_data)

    if not result:
        raise HTTPException(status_code=404, detail="Reaction not found or update failed")

    return result
