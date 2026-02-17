from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str | None = None
    message: str
    field: str | None = None


class EnvelopeResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    errors: list[ErrorDetail] | list[dict] | dict | None = None
    meta: dict | None = None


def build_success_envelope(
    *,
    data: object,
    message: str = "Success",
    meta: dict | None = None,
) -> dict:
    payload: dict[str, object] = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    return payload


def build_error_envelope(
    *,
    message: str,
    errors: list[dict] | dict | None = None,
) -> dict:
    payload: dict[str, object] = {
        "success": False,
        "message": message,
        "data": None,
    }
    if errors is not None:
        payload["errors"] = errors
    return payload

