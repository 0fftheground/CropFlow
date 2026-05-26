from __future__ import annotations

import contextvars
import json
import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import Request

_REQUEST_ID_VAR: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s"


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    request_context_filter = RequestContextFilter()
    formatter = logging.Formatter(_LOG_FORMAT)
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.addFilter(request_context_filter)
        root_logger.addHandler(handler)
        return

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        if not any(isinstance(existing_filter, RequestContextFilter) for existing_filter in handler.filters):
            handler.addFilter(request_context_filter)


def set_request_id(request_id: str | None = None) -> contextvars.Token[str]:
    actual_request_id = request_id or uuid4().hex[:12]
    return _REQUEST_ID_VAR.set(actual_request_id)


def reset_request_id(token: contextvars.Token[str]) -> None:
    _REQUEST_ID_VAR.reset(token)


def get_request_id() -> str:
    return _REQUEST_ID_VAR.get()


def summarize_for_log(value: Any, *, max_length: int = 1200, max_items: int = 20) -> str:
    try:
        normalized = _normalize_for_log(value, max_items=max_items)
        text = json.dumps(normalized, ensure_ascii=False, default=str, separators=(",", ":"))
    except TypeError:
        text = repr(value)
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}...<truncated {len(text) - max_length} chars>"


async def extract_request_context(request: Request, *, include_body: bool) -> dict[str, Any]:
    context: dict[str, Any] = {
        "requestId": getattr(request.state, "request_id", get_request_id()),
        "method": request.method,
        "path": request.url.path,
        "query": dict(request.query_params),
        "pathParams": dict(request.path_params),
    }
    route = request.scope.get("route")
    if route is not None and getattr(route, "name", None):
        context["route"] = route.name
    client = request.client
    if client is not None:
        context["client"] = f"{client.host}:{client.port}"
    if include_body:
        context["body"] = await _summarize_request_body(request)
    return context


def log_api_response_summary(
    logger: logging.Logger,
    request: Request,
    *,
    status_code: int,
    duration_ms: float,
) -> None:
    logger.info(
        "API request completed method=%s path=%s status=%s duration_ms=%.2f query=%s",
        request.method,
        request.url.path,
        status_code,
        duration_ms,
        summarize_for_log(dict(request.query_params)),
    )


class LogTimer:
    def __init__(self) -> None:
        self._started_at = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._started_at) * 1000


async def _summarize_request_body(request: Request) -> str:
    body = await request.body()
    if not body:
        return "<empty>"
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary {len(body)} bytes>"
    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        return summarize_for_log(decoded)
    return summarize_for_log(parsed)


def _normalize_for_log(value: Any, *, max_items: int) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                normalized["..."] = f"{len(value) - max_items} more keys"
                break
            normalized[str(key)] = _normalize_for_log(item, max_items=max_items)
        return normalized
    if isinstance(value, list | tuple):
        items = [_normalize_for_log(item, max_items=max_items) for item in value[:max_items]]
        if len(value) > max_items:
            items.append(f"... {len(value) - max_items} more items")
        return items
    if isinstance(value, bytes):
        return f"<bytes {len(value)}>"
    return value
