from fastapi import APIRouter, Depends, HTTPException, Path, status

from security.auth import verify_any_token
from schemas.listing_schema import PaginatedListOut
from schemas.author_room import AuthorRoomBase, AuthorRoomCreate, AuthorRoomOut, AuthorRoomUpdate
from services.author_room_service import (
    add_author_room,
    remove_author_room,
    retrieve_author_room_by_author_room_id,
    retrieve_author_rooms,
    retrieve_author_rooms_count,
    update_author_room_by_id,
)
from services.listing_service import build_list_payload, clamp_limit

router = APIRouter(prefix="/author_room", tags=["AuthorRooms-v2"])


@router.get("/", response_model=PaginatedListOut[AuthorRoomOut])
async def list_author_rooms(
    skip: int = 0,
    limit: int = 20,
    dep=Depends(verify_any_token),
):
    if skip < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_author_rooms(start=skip, stop=skip + safe_limit)
    total = await retrieve_author_rooms_count()
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


@router.get("/{id}", response_model=AuthorRoomOut)
async def get_author_room_by_id(dep=Depends(verify_any_token),id: str = Path(..., description="Author room ID")):
    item = await retrieve_author_room_by_author_room_id(id=id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AuthorRoom not found")
    return item


@router.post("/", response_model=AuthorRoomOut, status_code=status.HTTP_201_CREATED)
async def create_a_comment_in_author_room(payload: AuthorRoomBase,dep=Depends(verify_any_token),):
    item = await add_author_room(AuthorRoomCreate(**payload.model_dump()))
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create author room")
    return item


@router.patch("/{id}", response_model=AuthorRoomOut)
async def update_a_comment_in_author_room(
    id: str = Path(..., description="ID of the author room to update"),
    payload: AuthorRoomUpdate = ..., # type: ignore
     dep=Depends(verify_any_token),
):
    updated = await update_author_room_by_id(author_room_id=id, author_room_data=payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AuthorRoom not found")
    return updated


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_a_comment_in_author_room(id: str = Path(..., description="ID of the author room to delete")):
    deleted = await remove_author_room(id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AuthorRoom not found")
    return {"deleted": True}
