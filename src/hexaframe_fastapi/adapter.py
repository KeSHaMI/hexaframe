from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Type,
    Union,
    get_origin,
)

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
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
    use_case: Union[UseCase[Any, Any], AsyncUseCase[Any, Any]] | None = None,
    use_case_factory: Optional[
        Callable[[], Union[UseCase[Any, Any], AsyncUseCase[Any, Any]]]
    ] = None,
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

    # Validate inputs: either direct use_case
    # or a factory must be provided, but not both.
    if (use_case is None and use_case_factory is None) or (
        use_case is not None and use_case_factory is not None
    ):
        raise ValueError("Provide exactly one of 'use_case' or 'use_case_factory'.")

    http_method = method.lower()
    if http_method not in {"get", "post", "put", "patch", "delete"}:
        raise ValueError(f"Unsupported method: {method}")

    # Note: we keep a generic body: Mapping type to remain framework-agnostic,
    # but allow FastAPI to attach response_model and docs via route registration below.
    async def handler(
        body: Optional[Mapping[str, Any]] = None,
        uc: Union[UseCase[Any, Any], AsyncUseCase[Any, Any]] | None = None,
    ) -> JSONResponse:
        payload = body or {}
        try:
            # Resolve UseCase instance: prefer dependency-injected factory if provided.
            the_uc: Union[UseCase[Any, Any], AsyncUseCase[Any, Any]]
            if uc is not None:
                the_uc = uc
            else:
                # Fallback for direct instance mode
                assert use_case is not None
                the_uc = use_case

            uc_input = input_parser(payload) if input_parser else payload
            if isinstance(the_uc, AsyncUseCase):
                res: Result[Any, HexaError] = await the_uc.execute(uc_input)  # type: ignore[arg-type]
            else:
                res = the_uc.execute(uc_input)  # type: ignore[arg-type]
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

    # If users pass a Pydantic model as response_model, keep it.
    # Otherwise, try to infer from output_mapper annotation.
    # Additionally, attach __annotations__ to
    # handler so FastAPI can build better OpenAPI
    # when input_parser/output_mapper provide annotated types.
    # This keeps runtime signature simple
    # but enhances docs.
    # Attempt to discover annotated input/output types:
    inferred_input_anno: Optional[Type[Any]] = None
    inferred_output_anno: Optional[Type[Any]] = None

    try:
        if input_parser is not None:
            in_hints = getattr(input_parser, "__annotations__", {})
            inferred_input_anno = in_hints.get("return") or in_hints.get("out") or None
    except Exception:
        inferred_input_anno = None

    try:
        if output_mapper is not None:
            out_hints = getattr(output_mapper, "__annotations__", {})
            inferred_output_anno = out_hints.get("return") or None
    except Exception:
        inferred_output_anno = None

    # Build synthetic annotations for FastAPI
    handler_annotations: Dict[str, Any] = dict(getattr(handler, "__annotations__", {}))
    # Prefer explicitly provided response_model over inferred
    if response_model is not None:
        handler_annotations["return"] = response_model
    elif inferred_output_anno is not None:
        handler_annotations["return"] = inferred_output_anno
    else:
        # Avoid annotating with JSONResponse to prevent FastAPI from attempting to
        # create a Pydantic model for a Response type. Use starlette Response.
        handler_annotations["return"] = Response

    # If we can infer a request model, expose it as "body" param type
    if inferred_input_anno is not None:
        handler_annotations["body"] = Optional[inferred_input_anno]  # type: ignore[index]

    handler.__annotations__ = handler_annotations
    # Register route with optional FastAPI documentation metadata
    route_register = getattr(router, http_method)
    # If no explicit response_model provided,
    # try to infer it from annotations we attached
    inferred_response_model: Optional[Type[Any]] = response_model
    if inferred_response_model is None:
        try:
            ret = handler.__annotations__.get("return")
            origin = get_origin(ret) or ret
            # If the inferred return type
            # is a Response type, do not set a response_model
            if isinstance(origin, type) and not issubclass(origin, Response):
                inferred_response_model = origin
            else:
                inferred_response_model = None
        except Exception:
            inferred_response_model = None

    route_kwargs: Dict[str, Any] = dict(
        summary=summary,
        description=description,
        tags=tags,
    )
    # Only pass response_model if
    # it's not None to avoid FastAPI trying to model Response
    if inferred_response_model is not None:
        route_kwargs["response_model"] = inferred_response_model

    # Ensure FastAPI treats the 'body' parameter as a JSON request body and does not
    # attempt to validate it with Pydantic (we validate inside UseCase). We do this by
    # explicitly marking it as Body(...) with arbitrary schema.
    from fastapi import Body  # local import to avoid hard dependency at module import

    async def _wrapped(
        body: Optional[Mapping[str, Any]] = Body(default=None),
        uc: Union[UseCase[Any, Any], AsyncUseCase[Any, Any]] = Depends(use_case_factory)  # type: ignore[arg-type]
        if use_case_factory is not None
        else Depends(lambda: use_case),  # type: ignore[arg-type]
    ) -> JSONResponse:  # type: ignore[valid-type]
        return await handler(body, uc)

    # Preserve annotations for OpenAPI generation
    _wrapped.__annotations__ = handler.__annotations__

    route = route_register(
        path,
        **route_kwargs,
    )
    route(_wrapped)  # attach handler

    return router
