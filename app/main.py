import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import (
    LogTimer,
    configure_logging,
    extract_request_context,
    get_request_id,
    log_api_response_summary,
    reset_request_id,
    set_request_id,
    summarize_for_log,
)

settings = get_settings()
resolved_log_level = getattr(logging, str(settings.log_level).upper(), logging.INFO)
configure_logging(level=resolved_log_level, log_dir=settings.log_dir)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")
    request_id_token = set_request_id(request_id)
    request.state.request_id = get_request_id()
    timer = LogTimer()
    try:
        response = await call_next(request)
        log_api_response_summary(
            logger,
            request,
            status_code=response.status_code,
            duration_ms=timer.elapsed_ms,
        )
        response.headers["X-Request-ID"] = request.state.request_id
        return response
    finally:
        reset_request_id(request_id_token)


@app.exception_handler(HTTPException)
async def http_exception_logging_handler(request: Request, exc: HTTPException) -> JSONResponse:
    context = await extract_request_context(request, include_body=True)
    log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        "API request failed with HTTPException status=%s detail=%s context=%s",
        exc.status_code,
        exc.detail,
        summarize_for_log(context),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_logging_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    context = await extract_request_context(request, include_body=True)
    logger.warning(
        "API request validation failed errors=%s context=%s",
        summarize_for_log(exc.errors()),
        summarize_for_log(context),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_logging_handler(request: Request, exc: Exception) -> JSONResponse:
    context = await extract_request_context(request, include_body=True)
    logger.exception(
        "API request raised unhandled exception context=%s",
        summarize_for_log(context),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": "cropflow", "status": "ok"}
