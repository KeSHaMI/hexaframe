from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from fastapi import APIRouter

from hexaframe.use_case import AsyncUseCase, UseCase

from .adapter import InputParser, OutputMapper, build_router, default_error_mapper


@dataclass
class EndpointConfig:
    method: str
    path: str
    input_parser: Optional[InputParser] = None
    output_mapper: Optional[OutputMapper] = None


def endpoint(
    *,
    method: str,
    path: str,
    input_parser: Optional[InputParser] = None,
    output_mapper: Optional[OutputMapper] = None,
) -> Callable[[Union[UseCase[Any, Any], AsyncUseCase[Any, Any]]], APIRouter]:
    """
    Decorator to bind a UseCase/AsyncUseCase to a FastAPI APIRouter.
    Usage:

        @endpoint(method="post", path="/add-one")
        class AddOne(UseCase[dict, dict]): ...

        router = AddOne()  # instance of APIRouter

    Alternatively, instantiate the class and pass to build_router directly.
    """

    def wrapper(uc: Union[UseCase[Any, Any], AsyncUseCase[Any, Any]]) -> APIRouter:
        return build_router(
            path=path,
            method=method,
            use_case=uc,
            input_parser=input_parser,
            output_mapper=output_mapper,
            error_mapper=default_error_mapper,
        )

    return wrapper
