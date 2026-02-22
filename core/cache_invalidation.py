from __future__ import annotations

import inspect
from collections.abc import Iterable
from functools import wraps
from typing import Any, Callable

from pydantic import BaseModel

from core.entity_cache import (
    invalidate_book_summary,
    invalidate_chapter_summary,
    invalidate_page_summary,
)


def _as_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _read_field(payload: Any, field_name: str) -> Any:
    if payload is None:
        return None
    if isinstance(payload, BaseModel):
        return getattr(payload, field_name, None)
    if isinstance(payload, dict):
        return payload.get(field_name)
    return getattr(payload, field_name, None)


def _extract_ids_from_response(response: Any, field_names: Iterable[str]) -> set[str]:
    found: set[str] = set()
    targets = response if isinstance(response, list) else [response]
    for target in targets:
        for field_name in field_names:
            value = _read_field(target, field_name)
            for item in _as_values(value):
                if item is not None:
                    found.add(str(item))
    return found


def _extract_ids_from_args(bound_arguments: dict[str, Any], arg_names: Iterable[str]) -> set[str]:
    found: set[str] = set()
    for arg_name in arg_names:
        value = bound_arguments.get(arg_name)
        for item in _as_values(value):
            if item is not None:
                found.add(str(item))
    return found


def invalidate_entity_cache(
    *,
    book_arg_names: tuple[str, ...] = (),
    chapter_arg_names: tuple[str, ...] = (),
    page_arg_names: tuple[str, ...] = (),
    book_response_fields: tuple[str, ...] = (),
    chapter_response_fields: tuple[str, ...] = (),
    page_response_fields: tuple[str, ...] = (),
) -> Callable:
    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            result = await func(*args, **kwargs)

            book_ids = _extract_ids_from_args(bound.arguments, book_arg_names)
            book_ids.update(_extract_ids_from_response(result, book_response_fields))

            chapter_ids = _extract_ids_from_args(bound.arguments, chapter_arg_names)
            chapter_ids.update(_extract_ids_from_response(result, chapter_response_fields))

            page_ids = _extract_ids_from_args(bound.arguments, page_arg_names)
            page_ids.update(_extract_ids_from_response(result, page_response_fields))

            for book_id in book_ids:
                await invalidate_book_summary(book_id)
            for chapter_id in chapter_ids:
                await invalidate_chapter_summary(chapter_id)
            for page_id in page_ids:
                await invalidate_page_summary(page_id)

            return result

        return wrapper

    return decorator
