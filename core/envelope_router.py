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
            if response.status_code == 204:
                return response

            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return response

            try:
                raw = response.body.decode("utf-8") if response.body else ""
                payload = json.loads(raw) if raw else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                return response

            if _is_enveloped(payload):
                return response

            wrapped_data = jsonable_encoder(payload)
            message = "Success"

            # Legacy v1 shape: {"status_code": int, "data": ..., "detail": str}
            if isinstance(payload, dict) and {"status_code", "data", "detail"}.issubset(payload.keys()):
                wrapped_data = jsonable_encoder(payload.get("data"))
                detail = payload.get("detail")
                if isinstance(detail, str) and detail:
                    message = detail

            wrapped = build_success_envelope(
                data=wrapped_data,
                message=message,
            )
            headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
            return JSONResponse(
                status_code=response.status_code,
                content=wrapped,
                headers=headers,
            )

        return custom_route_handler
