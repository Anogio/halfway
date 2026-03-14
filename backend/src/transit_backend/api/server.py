from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from transit_backend.api.contracts import (
    build_health_payload,
    build_metadata_payload,
)
from transit_backend.api.geocoding import (
    GEOCODE_ACCEPT_LANGUAGE,
    GEOCODE_MAX_RESULTS,
    GEOCODE_PROVIDER_TIMEOUT_S,
    GEOCODE_PROVIDER_URL,
    GEOCODE_USER_AGENT,
    REVERSE_GEOCODE_PROVIDER_URL,
    router as geocoding_router,
)
from transit_backend.api.routing_handlers import (
    build_multi_isochrones_response,
    build_multi_path_response,
    build_wakeup_response,
)
from transit_backend.api.state import load_app_state, start_app_runtime, stop_app_runtime

__all__ = [
    "app",
    "APP_STATE",
    "GEOCODE_MAX_RESULTS",
    "GEOCODE_PROVIDER_TIMEOUT_S",
    "GEOCODE_PROVIDER_URL",
    "REVERSE_GEOCODE_PROVIDER_URL",
    "GEOCODE_USER_AGENT",
    "GEOCODE_ACCEPT_LANGUAGE",
    "require_cors_settings",
]


APP_STATE = load_app_state()


def require_cors_settings() -> tuple[list[str], str | None]:
    cors_origin = os.environ.get("CORS_ALLOW_ORIGIN", "").strip()
    cors_origin_regex = os.environ.get("CORS_ALLOW_ORIGIN_REGEX", "").strip()

    if cors_origin and cors_origin_regex:
        return [cors_origin], cors_origin_regex
    if cors_origin:
        return [cors_origin], None
    if cors_origin_regex:
        return [], cors_origin_regex
    raise RuntimeError("CORS_ALLOW_ORIGIN or CORS_ALLOW_ORIGIN_REGEX must be set")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state = getattr(app.state, "app_state", None)
    if isinstance(app_state, dict):
        start_app_runtime(app_state)
    try:
        yield
    finally:
        app_state = getattr(app.state, "app_state", None)
        if isinstance(app_state, dict):
            stop_app_runtime(app_state)


cors_origins, cors_origin_regex = require_cors_settings()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.state.app_state = APP_STATE
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(geocoding_router)


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def _request_validation_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "invalid request body"})


@app.get("/health")
def get_health(request: Request) -> dict[str, object]:
    app_state = request.app.state.app_state
    cfg = app_state["config"]
    return build_health_payload(cfg.settings)


@app.get("/metadata")
def get_metadata(request: Request) -> dict[str, object]:
    app_state = request.app.state.app_state
    cfg = app_state["config"]
    return build_metadata_payload(cfg.settings)


@app.post("/multi_isochrones")
async def post_multi_isochrones(request: Request) -> dict[str, object]:
    payload = await _read_payload(request)
    return build_multi_isochrones_response(request.app.state.app_state, payload)


@app.post("/multi_path")
async def post_multi_path(request: Request) -> dict[str, object]:
    payload = await _read_payload(request)
    return build_multi_path_response(request.app.state.app_state, payload)


@app.post("/wakeup")
async def post_wakeup(request: Request) -> dict[str, object]:
    payload = await _read_payload(request)
    return build_wakeup_response(request.app.state.app_state, payload)


async def _read_payload(request: Request) -> dict[str, object]:
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid request body") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid request body")
    return payload


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("transit_backend.api.server:app", host=host, port=port)


if __name__ == "__main__":
    main()
