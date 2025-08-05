from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Type, Union, get_origin

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from hexaframe.errors import (
    Conflict,
    HexaError,
    InfraError,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from hexaframe.result import Ok, Result
from hexaframe.types import to_serializable
from hexaframe.use_case import AsyncUseCase, UseCase

JSONDict = Dict[str, Any]
InputParser = Callable[[Mapping[str, Any]], Any]
OutputMapper = Callable[[Any], Mapping[str, Any]]


@dataclass
class ErrorMapping:
    status_code: int
    code: Optional[str] = None


DEFAULT_ERROR_TABLE: Dict[Type[HexaError], ErrorMapping] = {
    ValidationError: ErrorMapping(HTTP_422_UNPROCESSABLE_ENTITY, "validation_error"),
    NotFound: ErrorMapping(HTTP_404_NOT_FOUND, "not_found"),
    Conflict: ErrorMapping(HTTP_409_CONFLICT, "conflict"),
    PermissionDenied: ErrorMapping(HTTP_403_FORBIDDEN, "permission_denied"),
    InfraError: ErrorMapping(HTTP_500_INTERNAL_SERVER_ERROR, "infra_error"),
}


def default_error_mapper(err: HexaError) -> JSONResponse:
    for etype, mapping in DEFAULT_ERROR_TABLE.items():
        if isinstance(err, etype):
            payload = {
                "error": {
                    "code": err.code
                    if getattr(err, "code", None)
                    else (mapping.code or "error"),
                    "message": err.message
                    if getattr(err, "message", None)
                    else str(err),
                    "details": dict(err.details)
                    if getattr(err, "details", None)
                    else None,
                }
            }
            return JSONResponse(status_code=mapping.status_code, content=payload)
    payload = {
        "error": {
            "code": getattr(err, "code", "error"),
            "message": getattr(err, "message", str(err)),
            "details": dict(getattr(err, "details"))
            if getattr(err, "details", None)
            else None,
        }
    }
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content=payload)


def build_router(
    *,
    path: str,
    method: str,
    use_case: Union[UseCase[Any, Any], AsyncUseCase[Any, Any]],
    input_parser: Optional[InputParser] = None,
    output_mapper: Optional[OutputMapper] = None,
    error_mapper: Callable[[HexaError], JSONResponse] = default_error_mapper,
    # FastAPI route metadata (optional)
    response_model: Optional[Type[Any]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> APIRouter:
    """
    Build an APIRouter that exposes the provided UseCase or AsyncUseCase
    at the given path/method.
    - input_parser: converts request body dict into the UC input DTO
      (if None, pass the dict as-is)
    - output_mapper: converts UC output to a dict
      (if None, use to_serializable best-effort)
    - error_mapper: maps HexaError -> JSONResponse with status code
    """
    router = APIRouter()

    http_method = method.lower()
    if http_method not in {"get", "post", "put", "patch", "delete"}:
        raise ValueError(f"Unsupported method: {method}")

    # Note: we keep a generic body: Mapping type to remain framework-agnostic,
    # but allow FastAPI to attach response_model and docs via route registration below.
    async def handler(body: Optional[Mapping[str, Any]] = None) -> JSONResponse:
        payload = body or {}
        try:
            uc_input = input_parser(payload) if input_parser else payload
            if isinstance(use_case, AsyncUseCase):
                res: Result[Any, HexaError] = await use_case.execute(uc_input)  # type: ignore[arg-type]
            else:
                res = use_case.execute(uc_input)  # type: ignore[arg-type]
            if isinstance(res, Ok):
                out = res.unwrap()
                mapped = output_mapper(out) if output_mapper else to_serializable(out)
                # Ensure JSON-serializable content.
                # If a Pydantic model or dataclass slips through,
                # convert it to a dict using to_serializable() best-effort mapping.
                serializable_content: Mapping[str, Any]
                if isinstance(mapped, Mapping):
                    serializable_content = {
                        k: to_serializable(v) for k, v in mapped.items()
                    }
                else:
                    serializable_content = {"data": to_serializable(mapped)}
                return JSONResponse(
                    status_code=HTTP_200_OK,
                    content=serializable_content,
                )
            else:
                return error_mapper(res.unwrap_err())
        except HexaError as he:
            return error_mapper(he)

    # Register route with optional FastAPI documentation metadata
    route_register = getattr(router, http_method)
    # If no explicit response_model provided, try to infer it from output_mapper
    inferred_response_model: Optional[Type[Any]] = response_model
    if inferred_response_model is None and output_mapper is not None:
        # Heuristic: if output_mapper has an annotation
        # returning a Pydantic BaseModel-like type,
        # use it. Otherwise, leave as None and FastAPI will infer.
        try:
            ret = getattr(output_mapper, "__annotations__", {}).get("return")
            # unwrap typing like typing.Annotated / typing.Optional
            origin = get_origin(ret) or ret
            if isinstance(origin, type):
                inferred_response_model = origin  # type: ignore[assignment]
        except Exception:
            inferred_response_model = None

    route = route_register(
        path,
        response_model=inferred_response_model,
        summary=summary,
        description=description,
        tags=tags,
    )
    route(handler)  # attach handler

    return router
