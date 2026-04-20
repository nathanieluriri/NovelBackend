from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request

from repositories.tokens_repo import delete_refresh_token
from schemas.google_oauth_schema import GoogleOAuthExchangeRequest, GoogleOAuthTargetEnum
from schemas.reading_progress_schema import ReadingProgressOut
from schemas.tokens_schema import refreshTokenRequest
from schemas.user_schema import (
    NewUserBase,
    NewUserCreate,
    NewUserOut,
    OldUserBase,
    OldUserOut,
    Provider,
    UserOutChapterDetails,
    UserStatus,
    UserUpdate,
)
from security.auth import verify_admin_token, verify_token, verify_token_and_refresh_token
from services.admin_services import get_all_user_details, get_one_user_details, update_user_details
from services.google_oauth_service import (
    exchange_google_oauth_code,
    handle_google_oauth_callback,
    start_google_oauth,
)
from services.reading_progress_service import get_user_reading_progress
from services.user_service import (
    change_of_user_password_flow1,
    change_of_user_password_flow2,
    get_user_details_with_accessToken,
    login_credentials,
    register_user,
    update_user,
)


router = APIRouter()


def _raise_google_body_auth_disabled() -> None:
    raise HTTPException(
        status_code=400,
        detail="Google OAuth now uses /api/v1/user/google/auth and /api/v1/user/google/exchange",
    )


@router.get("/google/auth")
async def login_with_google(
    request: Request,
    target: GoogleOAuthTargetEnum | None = Query(
        default=None,
        description=(
            "Frontend environment to return the user to after authentication. "
            "Must be an alias registered in GOOGLE_OAUTH_REDIRECT_TARGETS."
        ),
    ),
    redirect_path: str | None = Query(
        default=None,
        description=(
            "Relative path the frontend should send the user back to after "
            "login (e.g. '/settings'). Must start with a single '/'; absolute "
            "URLs and protocol-relative paths are rejected. Forwarded to the "
            "frontend as the ?redirect_path= query parameter on the success URL."
        ),
        max_length=512,
    ),
):
    return await start_google_oauth(
        request=request,
        target_alias=target.value if target is not None else None,
        redirect_path=redirect_path,
    )


@router.get("/google/callback")
@router.get("/auth/callback")
async def google_auth_callback(request: Request):
    return await handle_google_oauth_callback(request)


@router.post("/google/exchange", response_model_exclude_none=True, response_model=OldUserOut)
async def exchange_google_login(exchange_request: GoogleOAuthExchangeRequest):
    return await exchange_google_oauth_code(exchange_request)


@router.post("/sign-up", response_model=NewUserOut)
async def register(user: NewUserBase):
    if user.provider == Provider.GOOGLE:
        _raise_google_body_auth_disabled()

    user_to_create = NewUserCreate(**user.model_dump())
    await user_to_create.model_async_validate()
    try:
        return await register_user(user_to_create)
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@router.post("/sign-in", response_model_exclude_none=True, response_model=OldUserOut)
async def login(user_data: OldUserBase):
    if user_data.provider == Provider.GOOGLE:
        _raise_google_body_auth_disabled()

    try:
        return await login_credentials(user_data=user_data)
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@router.post("/refresh")
async def refresh_access_token(
    refreshObj: refreshTokenRequest,
    dep=Depends(verify_token_and_refresh_token),
):
    result = await delete_refresh_token(refreshToken=refreshObj.refreshToken)
    if result:
        return dep
    raise HTTPException(status_code=404, detail="Refresh Token is Invalid")


@router.get("/details", response_model_exclude_none=True, dependencies=[Depends(verify_token)])
async def get_user_details(accessToken: str = Depends(verify_token)) -> NewUserOut:
    user = await get_user_details_with_accessToken(token=accessToken["accessToken"])
    if user:
        return user
    raise HTTPException(status_code=404, detail="Details not found")


@router.get(
    "/reading/progress",
    response_model=ReadingProgressOut,
    response_model_exclude_none=True,
    dependencies=[Depends(verify_token)],
)
async def get_stopped_reading_progress(accessToken: str = Depends(verify_token)):
    user = await get_user_details_with_accessToken(token=accessToken["accessToken"])
    if not user:
        raise HTTPException(status_code=404, detail="Details not found")
    return await get_user_reading_progress(user=user)


@router.post("/initiate/change-password")
async def initiate_change_of_user_password_process(
    email=Body(title="email", description="Enter your email", alias="email"),
):
    await change_of_user_password_flow1(email=email["email"])
    return {"message": "Success"}


@router.post("/conclude/change-password")
async def conclude_change_of_user_password_process(
    email=Body(title="email", description="Enter your email", alias="email"),
    otp=Body(title="otp", description="Enter your otp", alias="otp"),
    password=Body(title="password", description="Enter your password", alias="password"),
):
    result = await change_of_user_password_flow2(email=email, otp=otp, password=password)
    return {"message": result}


@router.patch("/update", response_model_exclude_none=True, dependencies=[Depends(verify_token)])
async def update(update: UserUpdate, accessToken: str = Depends(verify_token)) -> NewUserOut:
    await update_user(token=accessToken["accessToken"], update=update)
    user = await get_user_details_with_accessToken(token=accessToken["accessToken"])
    if user:
        return user
    raise HTTPException(status_code=404, detail="Details not found")


@router.get(
    "/all/user-details",
    description="Requires admin Tokens",
    response_model_exclude_none=True,
    dependencies=[Depends(verify_admin_token)],
)
async def get_user_data():
    result = await get_all_user_details()
    if result:
        return result
    raise HTTPException(status_code=404, detail="No user details found")


@router.get(
    "/{userId}/user-details",
    response_model=UserOutChapterDetails,
    description="Requires admin Tokens",
    response_model_exclude_none=True,
    dependencies=[Depends(verify_admin_token)],
)
async def get_particular_user_data(
    userId: str = Path(..., description="The ID of the user whose status is to be updated."),
):
    result = await get_one_user_details(userId=userId)
    if result:
        return result
    raise HTTPException(status_code=404, detail="User details not found")


@router.patch(
    "/{userId}/status/{new_status}",
    description="Requires admin Tokens",
    response_model_exclude_none=True,
    dependencies=[Depends(verify_admin_token)],
)
async def update_user_data(
    userId: str = Path(..., description="The ID of the user whose status is to be updated."),
    new_status: UserStatus = Path(
        ...,
        description="The new status for the user (active, suspended, or inactive).",
    ),
):
    user = UserUpdate(status=new_status)
    result = await update_user_details(updateData=user, userId=userId)
    if result:
        return result
    raise HTTPException(status_code=404, detail="User status update failed")
