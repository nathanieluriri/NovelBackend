from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from schemas.response_schema import APIResponse
from schemas.listing_schema import PaginatedListOut
from schemas.reaction import (
    ReactionBase,
    ReactionCreate,
    ReactionOut,
    ReactionUpdate,
)
from services.reaction_service import (
    add_reaction,
    remove_reaction_for_user,
    retrieve_reaction_by_room,
    retrieve_reactions,
    retrieve_reactions_count,
    update_reaction_by_id,
)
from security.auth import verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
from services.listing_service import build_list_payload, clamp_limit
from services.user_service import get_user_details_with_accessToken

router = APIRouter(prefix="/reactions", tags=["Reactions"])


async def _get_actor_user_id(dep: dict) -> str:
    if dep["role"] == "member":
        user = await get_user_details_with_accessToken(token=dep["accessToken"])
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user.userId # type: ignore

    admin = await get_admin_details_with_accessToken_service(token=dep["accessToken"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return admin.userId # type: ignore


# ------------------------------
# List Reactions (with pagination and filtering)
# ------------------------------
@router.get("/", response_model=PaginatedListOut[ReactionOut])
async def list_reactions(
    skip: int = Query(0, description="Skip"),
    limit: int = Query(20, description="Limit"),
):
    if skip < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="skip must be >= 0")
    safe_limit = clamp_limit(limit)
    items = await retrieve_reactions(start=skip, stop=skip + safe_limit)
    total = await retrieve_reactions_count()
    return build_list_payload(items, skip=skip, limit=safe_limit, total=total)


# ------------------------------
# Retrieve a single Reaction
# ------------------------------
@router.get("/{authorRoomId}", response_model=APIResponse[ReactionOut])
async def get_reaction_for_room(
    authorRoomId: str = Path(..., description="Author room ID to fetch caller's reaction"),
    dep=Depends(verify_any_token),
):
    """Retrieve the caller's reaction for the given author room."""
    user_id = await _get_actor_user_id(dep)
    item = await retrieve_reaction_by_room(author_room_id=authorRoomId)
    return APIResponse(status_code=200, data=item, detail="Reaction fetched")


# ------------------------------
# Create a new Reaction
# ------------------------------
# Uses ReactionBase for input (correctly)
@router.post("/", response_model=APIResponse[ReactionOut], status_code=status.HTTP_201_CREATED)
async def create_reaction(payload: ReactionBase, dep=Depends(verify_any_token)):
    """
    Creates a new Reaction.
    """
    user_id = await _get_actor_user_id(dep)
    # Creates ReactionCreate object which includes date_created/last_updated
    new_data = ReactionCreate(**payload.model_dump(), userId=user_id)
    new_item = await add_reaction(new_data)
    if not new_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create reaction")
    
    return APIResponse(status_code=201, data=new_item, detail=f"Reaction created successfully")


# ------------------------------
# Update an existing Reaction
# ------------------------------
# Uses PATCH for partial update (correctly)
@router.patch("/{authorRoomId}", response_model=APIResponse[ReactionOut])
async def update_reaction(
    payload: ReactionUpdate,
    authorRoomId: str = Path(..., description="ID of the author room whose reaction to update"),
    dep=Depends(verify_any_token),
):
    """Updates the caller's reaction in the specified author room."""

    user_id = await _get_actor_user_id(dep)
    updated_item = await update_reaction_by_id(
        user_id=user_id, author_room_id=authorRoomId, reaction_data=payload
    )
    return APIResponse(status_code=200, data=updated_item, detail="Reaction updated successfully")


# ------------------------------
# Delete an existing Reaction
# ------------------------------
@router.delete("/{authorRoomId}", response_model=APIResponse[None])
async def delete_reaction(authorRoomId: str = Path(..., description="Author room whose reaction to delete"), dep=Depends(verify_any_token)):
    """Delete the caller's reaction for the specified author room."""
    user_id = await _get_actor_user_id(dep)
    deleted = await remove_reaction_for_user(user_id=user_id, author_room_id=authorRoomId)
    return APIResponse(status_code=200, data=None, detail="Reaction deleted successfully")
