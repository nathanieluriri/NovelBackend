from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette import routing
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


def _resolve_schema_ref(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in schema:
        return schema
    ref = schema["$ref"]
    if not isinstance(ref, str):
        return schema
    schema_name = ref.rsplit("/", 1)[-1]
    resolved = components.get(schema_name)
    if isinstance(resolved, dict):
        return resolved
    return schema


def _extract_data_schema_from_legacy_api_response(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    resolved = _resolve_schema_ref(schema, components)
    if "allOf" in resolved and isinstance(resolved["allOf"], list) and len(resolved["allOf"]) == 1:
        item = resolved["allOf"][0]
        if isinstance(item, dict):
            resolved = _resolve_schema_ref(item, components)

    properties = resolved.get("properties")
    if isinstance(properties, dict) and "data" in properties and (
        "status_code" in properties or "detail" in properties
    ):
        data_schema = properties.get("data")
        if isinstance(data_schema, dict):
            return deepcopy(data_schema)

    return deepcopy(schema)


def _is_envelope_schema(schema: dict[str, Any], components: dict[str, Any]) -> bool:
    resolved = _resolve_schema_ref(schema, components)
    properties = resolved.get("properties")
    if not isinstance(properties, dict):
        return False
    return {"success", "message", "data"}.issubset(properties.keys())


def _build_envelope_schema(data_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": True},
            "message": {"type": "string", "example": "Success"},
            "data": data_schema,
        },
        "required": ["success", "message", "data"],
    }


def custom_v2_openapi() -> dict[str, Any]:
    if v2_app.openapi_schema:
        return v2_app.openapi_schema

    openapi_schema = get_openapi(
        title=v2_app.title,
        version=v2_app.version,
        description=v2_app.description,
        routes=v2_app.routes,
    )
    components = openapi_schema.get("components", {}).get("schemas", {})

    for path_item in openapi_schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            if not isinstance(responses, dict):
                continue

            for status_code, response_info in responses.items():
                if not str(status_code).startswith("2"):
                    continue
                if str(status_code) == "204":
                    continue
                if not isinstance(response_info, dict):
                    continue

                content = response_info.get("content")
                if not isinstance(content, dict):
                    continue
                app_json = content.get("application/json")
                if not isinstance(app_json, dict):
                    continue
                schema = app_json.get("schema")
                if not isinstance(schema, dict):
                    continue
                if _is_envelope_schema(schema, components):
                    continue

                data_schema = _extract_data_schema_from_legacy_api_response(schema, components)
                app_json["schema"] = _build_envelope_schema(data_schema)

    v2_app.openapi_schema = openapi_schema
    return v2_app.openapi_schema


v2_app.openapi = custom_v2_openapi


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


def include_router_with_envelope(
    target: APIRouter,
    source: APIRouter,
    *,
    prefix: str = "",
    tags: list[str] | None = None,
    dependencies: list | None = None,
) -> None:
    extra_tags = tags or []
    extra_dependencies = dependencies or []

    for route in source.routes:
        if isinstance(route, APIRoute):
            target.add_api_route(
                prefix + route.path,
                route.endpoint,
                response_model=route.response_model,
                status_code=route.status_code,
                tags=[*extra_tags, *(route.tags or [])],
                dependencies=[*extra_dependencies, *(route.dependencies or [])],
                summary=route.summary,
                description=route.description,
                response_description=route.response_description,
                responses=route.responses,
                deprecated=route.deprecated,
                methods=list(route.methods or []),
                operation_id=route.operation_id,
                response_model_include=route.response_model_include,
                response_model_exclude=route.response_model_exclude,
                response_model_by_alias=route.response_model_by_alias,
                response_model_exclude_unset=route.response_model_exclude_unset,
                response_model_exclude_defaults=route.response_model_exclude_defaults,
                response_model_exclude_none=route.response_model_exclude_none,
                include_in_schema=route.include_in_schema,
                response_class=route.response_class,
                name=route.name,
                callbacks=route.callbacks,
                openapi_extra=route.openapi_extra,
                generate_unique_id_function=route.generate_unique_id_function,
                route_class_override=EnvelopeAPIRoute,
            )
        elif isinstance(route, routing.Route):
            target.add_route(
                prefix + route.path,
                route.endpoint,
                methods=list(route.methods or []),
                include_in_schema=route.include_in_schema,
                name=route.name,
            )
        elif isinstance(route, APIWebSocketRoute):
            target.add_api_websocket_route(
                prefix + route.path,
                route.endpoint,
                dependencies=[*extra_dependencies, *(route.dependencies or [])],
                name=route.name,
            )
        elif isinstance(route, routing.WebSocketRoute):
            target.add_websocket_route(prefix + route.path, route.endpoint, name=route.name)


v2_router = APIRouter()
include_router_with_envelope(v2_router, admin.router, prefix="/admin", tags=["Admin-v2"])
include_router_with_envelope(v2_router, user.router, prefix="/user", tags=["User-v2"])
include_router_with_envelope(
    v2_router,
    book.router,
    prefix="/book",
    tags=["Book-v2"],
    dependencies=[Depends(verify_admin_token)],
)
include_router_with_envelope(v2_router, bookmark.router, prefix="/bookmark", tags=["Bookmark-v2"])
include_router_with_envelope(v2_router, like.router, prefix="/like", tags=["Like-v2"])
include_router_with_envelope(v2_router, chapter.router, prefix="/chapter", tags=["Chapter-v2"])
include_router_with_envelope(v2_router, page.router, prefix="/page", tags=["Page-v2"])
include_router_with_envelope(v2_router, comments.router, prefix="/comment", tags=["Comment-v2"])
include_router_with_envelope(v2_router, payment.router, prefix="/payment", tags=["Payment-v2"])
include_router_with_envelope(v2_router, author_room_v2.router)
include_router_with_envelope(v2_router, reaction_v2.router)
v2_app.include_router(v2_router)


# Mount versioned apps under a common /api root
app.mount("/api/v1", v1_app)
app.mount("/api/v2", v2_app)
