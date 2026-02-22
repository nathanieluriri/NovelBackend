# ============================================================================
# AUTHOR_ROOM SERVICE
# ============================================================================
# This file was auto-generated on: 2026-02-17 12:26:33 WAT
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.author_room import (
    count_author_rooms,
    create_author_room,
    get_author_room,
    get_author_rooms,
    update_author_room,
    delete_author_room,
)
from schemas.author_room import AuthorRoomCreate, AuthorRoomUpdate, AuthorRoomOut


async def add_author_room(author_room_data: AuthorRoomCreate) -> AuthorRoomOut:
    """adds an entry of AuthorRoomCreate to the database and returns an object

    Returns:
        _type_: AuthorRoomOut
    """
    return await create_author_room(author_room_data)


async def remove_author_room(author_room_id: str):
    """deletes a field from the database and removes AuthorRoomCreateobject 

    Raises:
        HTTPException 400: Invalid author_room ID format
        HTTPException 404:  AuthorRoom not found
    """
    if not ObjectId.is_valid(author_room_id):
        raise HTTPException(status_code=400, detail="Invalid author_room ID format")

    filter_dict = {"_id": ObjectId(author_room_id)}
    result = await delete_author_room(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="AuthorRoom not found")

    else: return True
    
async def retrieve_author_room_by_author_room_id(id: str) -> AuthorRoomOut:
    """Retrieves author_room object based specific Id 

    Raises:
        HTTPException 404(not found): if  AuthorRoom not found in the db
        HTTPException 400(bad request): if  Invalid author_room ID format

    Returns:
        _type_: AuthorRoomOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid author_room ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_author_room(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="AuthorRoom not found")

    return result


async def retrieve_author_rooms(start=0,stop=100) -> List[AuthorRoomOut]:
    """Retrieves AuthorRoomOut Objects in a list

    Returns:
        _type_: AuthorRoomOut
    """
    return await get_author_rooms(start=start,stop=stop)


async def retrieve_author_rooms_count() -> int:
    return await count_author_rooms()


async def update_author_room_by_id(author_room_id: str, author_room_data: AuthorRoomUpdate) -> AuthorRoomOut:
    """updates an entry of author_room in the database

    Raises:
        HTTPException 404(not found): if AuthorRoom not found or update failed
        HTTPException 400(not found): Invalid author_room ID format

    Returns:
        _type_: AuthorRoomOut
    """
    if not ObjectId.is_valid(author_room_id):
        raise HTTPException(status_code=400, detail="Invalid author_room ID format")

    filter_dict = {"_id": ObjectId(author_room_id)}
    result = await update_author_room(filter_dict, author_room_data)

    if not result:
        raise HTTPException(status_code=404, detail="AuthorRoom not found or update failed")

    return result
