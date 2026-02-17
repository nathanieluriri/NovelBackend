from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.security.auth import verify_any_token
from schemas.author_room import AuthorRoomBase, AuthorRoomCreate, AuthorRoomOut, AuthorRoomUpdate
from services.author_room_service import (
    add_author_room,
    remove_author_room,
    retrieve_author_room_by_author_room_id,
    retrieve_author_rooms,
    update_author_room_by_id,
)

router = APIRouter(prefix="/author_rooms", tags=["AuthorRooms-v2"])


@router.get("/", response_model=List[AuthorRoomOut])
async def list_author_rooms(
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for pagination (0-indexed)"),
    dep=Depends(verify_any_token),
):
    page_size = 50

    if start is not None or stop is not None:
        if start is None or stop is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both 'start' and 'stop' are required")
        if stop < start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'stop' cannot be less than 'start'")
        return await retrieve_author_rooms(start=start, stop=stop)

    if page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative")
        start_index = page_number * page_size
        stop_index = start_index + page_size
        return await retrieve_author_rooms(start=start_index, stop=stop_index)

    return await retrieve_author_rooms(start=0, stop=100)


@router.get("/{id}", response_model=AuthorRoomOut)
async def get_author_room_by_id(dep=Depends(verify_any_token),id: str = Path(..., description="Author room ID")):
    item = await retrieve_author_room_by_author_room_id(id=id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AuthorRoom not found")
    return item


@router.post("/", response_model=AuthorRoomOut, status_code=status.HTTP_201_CREATED)
async def create_author_room(payload: AuthorRoomBase,dep=Depends(verify_any_token),):
    item = await add_author_room(AuthorRoomCreate(**payload.model_dump()))
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create author room")
    return item


@router.patch("/{id}", response_model=AuthorRoomOut)
async def update_author_room(
    id: str = Path(..., description="ID of the author room to update"),
    payload: AuthorRoomUpdate = ..., # type: ignore
     dep=Depends(verify_any_token),
):
    updated = await update_author_room_by_id(author_room_id=id, author_room_data=payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AuthorRoom not found")
    return updated


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_author_room(id: str = Path(..., description="ID of the author room to delete")):
    deleted = await remove_author_room(id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AuthorRoom not found")
    return {"deleted": True}

