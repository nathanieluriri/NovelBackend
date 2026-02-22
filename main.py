from copy import deepcopy
from datetime import datetime, timezone
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
from api.v2 import (
    author_room as author_room_v2,
    book as book_v2,
    bookmark as bookmark_v2,
    chapter as chapter_v2,
    comments as comments_v2,
    like as like_v2,
    page as page_v2,
    payment as payment_v2,
    reaction as reaction_v2,
    user as user_v2,
)
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


def _choose_type(schema: dict[str, Any]) -> str | None:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return schema_type
    if isinstance(schema_type, list):
        for t in schema_type:
            if t != "null":
                return t
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    return None


def _example_string(field_name: str, schema: dict[str, Any]) -> str:
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return str(enum_values[0])

    schema_format = schema.get("format")
    if schema_format == "date-time":
        return datetime.now(timezone.utc).isoformat()
    if schema_format == "email":
        return "jane.doe@example.com"
    if schema_format == "uri":
        return "https://example.com/resource"

    key = field_name.lower()
    if key == "id" or key.endswith("id") or key.endswith("_id"):
        return "684662739b0b51aed9ecd188"
    if "email" in key:
        return "jane.doe@example.com"
    if "avatar" in key or "url" in key:
        return "https://example.com/avatar.jpg"
    if "firstname" in key:
        return "Jane"
    if "lastname" in key:
        return "Doe"
    if "phone" in key:
        return "+15551234567"
    if "role" in key:
        return "member"
    if "message" in key or "detail" in key:
        return "Request processed successfully"
    if "text" in key:
        return "This is a sample text"
    if "token" in key:
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sample.signature"
    return "string"


def _example_from_schema(
    schema: dict[str, Any],
    components: dict[str, Any],
    *,
    field_name: str = "",
    depth: int = 0,
) -> Any:
    if depth > 6:
        return None

    resolved = _resolve_schema_ref(schema, components)

    if "example" in resolved:
        return deepcopy(resolved["example"])
    if "default" in resolved and resolved["default"] is not None:
        return deepcopy(resolved["default"])

    one_of = resolved.get("oneOf")
    if isinstance(one_of, list) and one_of:
        first = one_of[0]
        if isinstance(first, dict):
            return _example_from_schema(first, components, field_name=field_name, depth=depth + 1)

    any_of = resolved.get("anyOf")
    if isinstance(any_of, list) and any_of:
        first = any_of[0]
        if isinstance(first, dict):
            return _example_from_schema(first, components, field_name=field_name, depth=depth + 1)

    all_of = resolved.get("allOf")
    if isinstance(all_of, list) and all_of:
        merged: dict[str, Any] = {}
        for item in all_of:
            if not isinstance(item, dict):
                continue
            val = _example_from_schema(item, components, field_name=field_name, depth=depth + 1)
            if isinstance(val, dict):
                merged.update(val)
            elif val is not None:
                return val
        if merged:
            return merged

    if isinstance(resolved.get("enum"), list) and resolved["enum"]:
        return deepcopy(resolved["enum"][0])

    schema_type = _choose_type(resolved)
    if schema_type == "object":
        result: dict[str, Any] = {}
        properties = resolved.get("properties")
        if isinstance(properties, dict):
            for prop_name, prop_schema in properties.items():
                if not isinstance(prop_schema, dict):
                    continue
                prop_value = _example_from_schema(
                    prop_schema,
                    components,
                    field_name=prop_name,
                    depth=depth + 1,
                )
                if prop_value is not None:
                    result[prop_name] = prop_value
        if result:
            return result

        additional = resolved.get("additionalProperties")
        if isinstance(additional, dict):
            additional_value = _example_from_schema(
                additional,
                components,
                field_name="value",
                depth=depth + 1,
            )
            return {"key": additional_value}
        return {}

    if schema_type == "array":
        items = resolved.get("items")
        if isinstance(items, dict):
            item_example = _example_from_schema(items, components, field_name=field_name, depth=depth + 1)
            if item_example is not None:
                return [item_example]
        return []

    if schema_type == "integer":
        minimum = resolved.get("minimum")
        if isinstance(minimum, int):
            return minimum
        return 1
    if schema_type == "number":
        minimum = resolved.get("minimum")
        if isinstance(minimum, (int, float)):
            return float(minimum)
        return 1.0
    if schema_type == "boolean":
        return True
    if schema_type == "string":
        return _example_string(field_name=field_name, schema=resolved)

    return None


def _success_message_for_status(status_code: str) -> str:
    messages = {
        "200": "Success",
        "201": "Resource created successfully",
        "202": "Request accepted",
        "204": "No content",
    }
    return messages.get(status_code, "Success")


def _error_message_for_status(status_code: str) -> str:
    messages = {
        "400": "Bad request",
        "401": "Not authenticated",
        "403": "Forbidden",
        "404": "Resource not found",
        "409": "Conflict",
        "422": "Validation failed",
        "500": "Internal Server Error",
    }
    return messages.get(status_code, "Request failed")


def _build_v2_error_example(status_code: str) -> dict[str, Any]:
    example: dict[str, Any] = {
        "success": False,
        "message": _error_message_for_status(status_code),
        "data": None,
    }
    if status_code == "422":
        example["errors"] = [
            {
                "type": "missing",
                "loc": ["body", "field"],
                "msg": "Field required",
                "input": None,
            }
        ]
    return example


def _build_v1_error_example(status_code: str) -> dict[str, Any]:
    if status_code == "422":
        return {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "field"],
                    "msg": "Field required",
                    "input": None,
                }
            ]
        }
    return {"detail": _error_message_for_status(status_code)}


def _inject_response_examples(openapi_schema: dict[str, Any], *, is_v2: bool) -> None:
    components = openapi_schema.get("components", {}).get("schemas", {})

    for path_item in openapi_schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses")
            if not isinstance(responses, dict):
                continue

            for status_code, response_info in responses.items():
                if not isinstance(response_info, dict):
                    continue
                content = response_info.get("content")
                if not isinstance(content, dict):
                    continue
                app_json = content.get("application/json")
                if not isinstance(app_json, dict):
                    continue
                if "example" in app_json or "examples" in app_json:
                    continue

                if is_v2 and not str(status_code).startswith("2"):
                    app_json["example"] = _build_v2_error_example(str(status_code))
                    continue
                if not is_v2 and not str(status_code).startswith("2"):
                    app_json["example"] = _build_v1_error_example(str(status_code))
                    continue

                schema = app_json.get("schema")
                if not isinstance(schema, dict):
                    continue
                generated = _example_from_schema(schema, components)
                if generated is None:
                    continue

                if (
                    is_v2
                    and isinstance(generated, dict)
                    and {"success", "message", "data"}.issubset(generated.keys())
                ):
                    generated["success"] = True
                    generated["message"] = _success_message_for_status(str(status_code))

                app_json["example"] = generated


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


def custom_v1_openapi() -> dict[str, Any]:
    if v1_app.openapi_schema:
        return v1_app.openapi_schema

    openapi_schema = get_openapi(
        title=v1_app.title,
        version=v1_app.version,
        description=v1_app.description,
        routes=v1_app.routes,
        servers=[{"url": "/api/v1", "description": "v1 base path"}],
    )
    _inject_response_examples(openapi_schema, is_v2=False)
    v1_app.openapi_schema = openapi_schema
    return v1_app.openapi_schema


def custom_v2_openapi() -> dict[str, Any]:
    if v2_app.openapi_schema:
        return v2_app.openapi_schema

    openapi_schema = get_openapi(
        title=v2_app.title,
        version=v2_app.version,
        description=v2_app.description,
        routes=v2_app.routes,
        servers=[{"url": "/api/v2", "description": "v2 base path"}],
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

    _inject_response_examples(openapi_schema, is_v2=True)
    v2_app.openapi_schema = openapi_schema
    return v2_app.openapi_schema


v1_app.openapi = custom_v1_openapi
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

    def has_http_conflict(path: str, methods: set[str]) -> bool:
        for existing in target.routes:
            if not isinstance(existing, (APIRoute, routing.Route)):
                continue
            if existing.path != path:
                continue
            existing_methods = set(existing.methods or [])
            if existing_methods & methods:
                return True
        return False

    for route in source.routes:
        if isinstance(route, APIRoute):
            route_methods = set(route.methods or [])
            if has_http_conflict(prefix + route.path, route_methods):
                continue
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
            route_methods = set(route.methods or [])
            if has_http_conflict(prefix + route.path, route_methods):
                continue
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
include_router_with_envelope(v2_router, user_v2.router, prefix="/user", tags=["User-v2"])
include_router_with_envelope(
    v2_router,
    book_v2.router,
    prefix="/book",
    tags=["Book-v2"],
    dependencies=[Depends(verify_admin_token)],
)
include_router_with_envelope(v2_router, bookmark_v2.router, prefix="/bookmark", tags=["Bookmark-v2"])
include_router_with_envelope(v2_router, like_v2.router, prefix="/like", tags=["Like-v2"])
include_router_with_envelope(v2_router, chapter_v2.router, prefix="/chapter", tags=["Chapter-v2"])
include_router_with_envelope(v2_router, page_v2.router, prefix="/page", tags=["Page-v2"])
include_router_with_envelope(v2_router, comments_v2.router, prefix="/comment", tags=["Comment-v2"])
include_router_with_envelope(v2_router, payment_v2.router, prefix="/payment", tags=["Payment-v2"])
include_router_with_envelope(v2_router, author_room_v2.router)
include_router_with_envelope(v2_router, reaction_v2.router)
include_router_with_envelope(v2_router, user.router, prefix="/user", tags=["User-v2-legacy"])
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
v2_app.include_router(v2_router)


# Mount versioned apps under a common /api root
app.mount("/api/v1", v1_app)
app.mount("/api/v2", v2_app)
