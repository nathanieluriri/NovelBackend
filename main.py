from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from api.v1 import admin, book, bookmark, chapter, comments, like, page, payment, user
from api.v2 import author_room as author_room_v2, reaction as reaction_v2
from core.envelope_router import EnvelopeAPIRoute
from core.response_envelope import build_error_envelope
from security.auth import verify_admin_token

# Root application
app = FastAPI(
    title="Mie Novel-app FastAPI Backend",
    summary="""Backend for the "Mie Novel-app", providing RESTful endpoints to manage users, novel content (books, chapters, pages), bookmarks, and likes. Features JWT-based authentication supporting both traditional credentials and Google sign-in, including token refresh capabilities.""",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Global middleware
app.add_middleware(SessionMiddleware, secret_key="some-random-string")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# --------------------
# v1 sub-application
# --------------------
v1_app = FastAPI(
    title="Mie Novel-app API v1",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

v1_app.include_router(admin.router, prefix="/admin", tags=["Admin"])
v1_app.include_router(user.router, prefix="/user", tags=["User"])
v1_app.include_router(book.router, prefix="/book", tags=["Book"], dependencies=[Depends(verify_admin_token)])
v1_app.include_router(bookmark.router, prefix="/bookmark", tags=["Bookmark"])
v1_app.include_router(like.router, prefix="/like", tags=["Like"])
v1_app.include_router(chapter.router, prefix="/chapter", tags=["Chapter"])
v1_app.include_router(page.router, prefix="/page", tags=["Page"])
v1_app.include_router(comments.router, prefix="/comment", tags=["Comment"])
v1_app.include_router(payment.router, prefix="/payment", tags=["Payment"])


# --------------------
# v2 sub-application
# --------------------
v2_app = FastAPI(
    title="Mie Novel-app API v2",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@v2_app.exception_handler(HTTPException)
async def v2_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed"
    errors = detail if isinstance(detail, (list, dict)) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(message=message, errors=errors),
    )


@v2_app.exception_handler(RequestValidationError)
async def v2_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            message="Validation failed",
            errors=exc.errors(),  # type: ignore
        ),
    )


@v2_app.exception_handler(Exception)
async def v2_unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=build_error_envelope(message="Internal Server Error"),
    )


v2_router = APIRouter(route_class=EnvelopeAPIRoute)
v2_router.include_router(admin.router, prefix="/admin", tags=["Admin-v2"])
v2_router.include_router(user.router, prefix="/user", tags=["User-v2"])
v2_router.include_router(book.router, prefix="/book", tags=["Book-v2"], dependencies=[Depends(verify_admin_token)])
v2_router.include_router(bookmark.router, prefix="/bookmark", tags=["Bookmark-v2"])
v2_router.include_router(like.router, prefix="/like", tags=["Like-v2"])
v2_router.include_router(chapter.router, prefix="/chapter", tags=["Chapter-v2"])
v2_router.include_router(page.router, prefix="/page", tags=["Page-v2"])
v2_router.include_router(comments.router, prefix="/comment", tags=["Comment-v2"])
v2_router.include_router(payment.router, prefix="/payment", tags=["Payment-v2"])
v2_router.include_router(author_room_v2.router)
v2_router.include_router(reaction_v2.router)
v2_app.include_router(v2_router)


# Mount versioned apps under a common /api root
app.mount("/api/v1", v1_app)
app.mount("/api/v2", v2_app)
