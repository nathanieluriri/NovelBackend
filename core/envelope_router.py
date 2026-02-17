from __future__ import annotations

import json
from typing import Callable

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from starlette.requests import Request

from core.response_envelope import build_success_envelope


def _is_enveloped(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    return {"success", "message", "data"}.issubset(payload.keys())


class EnvelopeAPIRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            response: Response = await original_route_handler(request)

            if response.status_code >= 400:
                return response
            if not isinstance(response, JSONResponse):
                return response

            try:
                raw = response.body.decode("utf-8")
                payload = json.loads(raw) if raw else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                return response

            if _is_enveloped(payload):
                return response

            wrapped = build_success_envelope(
                data=jsonable_encoder(payload),
                message="Success",
            )
            return JSONResponse(
                status_code=response.status_code,
                content=wrapped,
                headers=dict(response.headers),
            )

        return custom_route_handler

