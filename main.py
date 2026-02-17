from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from api.v1 import admin, book, bookmark, chapter, comments, like, page, payment, user
from api.v2 import author_room as author_room_v2
from core.envelope_router import EnvelopeAPIRoute
from core.response_envelope import build_error_envelope
from security.auth import verify_admin_token

app = FastAPI(
    root_path="/api/v1",
    title="Mie Novel-app FastAPI Backend",
    summary="""Backend for the "Mie Novel-app", providing RESTful endpoints to manage users, novel content (books, chapters, pages), bookmarks, and likes. Features JWT-based authentication supporting both traditional credentials and Google sign-in, including token refresh capabilities.""",
)

app.add_middleware(SessionMiddleware, secret_key="some-random-string")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_v2_request(request: Request) -> bool:
    return request.url.path.startswith("/api/v2")


@app.exception_handler(HTTPException)
async def http_exception_envelope_handler(request: Request, exc: HTTPException):
    if not _is_v2_request(request):
        return await http_exception_handler(request, exc)

    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed"
    errors = detail if isinstance(detail, (list, dict)) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(message=message, errors=errors),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_envelope_handler(request: Request, exc: RequestValidationError):
    if not _is_v2_request(request):
        return await request_validation_exception_handler(request, exc)

    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            message="Validation failed",
            errors=exc.errors(), # type: ignore
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_envelope_handler(request: Request, exc: Exception):
    if not _is_v2_request(request):
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    return JSONResponse(
        status_code=500,
        content=build_error_envelope(message="Internal Server Error"),
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(book.router, prefix="/book", tags=["Book"], dependencies=[Depends(verify_admin_token)])
app.include_router(bookmark.router, prefix="/bookmark", tags=["Bookmark"])
app.include_router(like.router, prefix="/like", tags=["Like"])
app.include_router(chapter.router, prefix="/chapter", tags=["Chapter"])
app.include_router(page.router, prefix="/page", tags=["Page"])
app.include_router(comments.router, prefix="/comment", tags=["Comment"])
app.include_router(payment.router, prefix="/payment", tags=["Payment"])

v2_router = APIRouter(prefix="/api/v2", route_class=EnvelopeAPIRoute)
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
app.include_router(v2_router)

 
