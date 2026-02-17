
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from typing import List, Optional
import json
from schemas.response_schema import APIResponse
from schemas.reaction import (
    ReactionCreate,
    ReactionOut,
    ReactionBase,
    ReactionUpdate,
)
from services.reaction_service import (
    add_reaction,
    remove_reaction_for_user,
    retrieve_reaction_by_room,
    retrieve_reaction_by_user_and_room,
    retrieve_reactions,
    update_reaction_by_id,
)
from security.auth import verify_any_token
from services.admin_services import get_admin_details_with_accessToken_service
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
@router.get("/", response_model=APIResponse[List[ReactionOut]])
async def list_reactions(
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    # New: Filter parameter expects a JSON string
  
):
    """
    Retrieves a list of Reactions with pagination and optional filtering.
    - Priority 1: Range-based (start/stop)
    - Priority 2: Page-based (page_number)
    - Priority 3: Default (first 100)
    """
    PAGE_SIZE = 50
    parsed_filters = {}

    # 1. Handle Filters
   
    # 2. Determine Pagination
    # Case 1: Prefer start/stop if provided
    if start is not None or stop is not None:
        if start is None or stop is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both 'start' and 'stop' must be provided together.")
        if stop < start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'stop' cannot be less than 'start'.")
        
        # Pass filters to the service layer
        items = await retrieve_reactions( start=start, stop=stop)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    # Case 2: Use page_number if provided
    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        # Pass filters to the service layer
        items = await retrieve_reactions(start=start_index, stop=stop_index)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {page_number} successfully")

    # Case 3: Default (no params)
    else:
        # Pass filters to the service layer
        items = await retrieve_reactions(start=0, stop=100)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            # If filters were applied, adjust the detail message
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)


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
