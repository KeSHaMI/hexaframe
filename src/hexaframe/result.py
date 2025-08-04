from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar, Union, overload

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class Result(Generic[T, E]):
    """
    A functional-style result type representing either success (Ok) or failure (Err).

    Pattern matching:

        match res:
            case Ok(value):
                ...
            case Err(error):
                ...

    Chaining:

        res.map(f).and_then(g)

    Async-aware helpers are provided to work with async functions returning Result.
    """

    def is_ok(self) -> bool:
        return isinstance(self, Ok)

    def is_err(self) -> bool:
        return isinstance(self, Err)

    @property
    def ok(self) -> T | None:
        return self.value if isinstance(self, Ok) else None  # type: ignore[attr-defined]

    @property
    def err(self) -> E | None:
        return self.error if isinstance(self, Err) else None  # type: ignore[attr-defined]

    # --- Transformations ---

    def map(self, fn: Callable[[T], U]) -> "Result[U, E]":
        if isinstance(self, Ok):
            return Ok(fn(self.value))
        return self  # type: ignore[return-value]

    def map_err(self, fn: Callable[[E], F]) -> "Result[T, F]":
        if isinstance(self, Err):
            return Err(fn(self.error))
        return self  # type: ignore[return-value]

    def and_then(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        if isinstance(self, Ok):
            return fn(self.value)
        return self  # type: ignore[return-value]

    # --- Async transformations (helpers for async pipelines) ---

    async def async_map(self, fn: Callable[[T], Awaitable[U]]) -> "Result[U, E]":
        if isinstance(self, Ok):
            return Ok(await fn(self.value))
        return self  # type: ignore[return-value]

    async def async_and_then(
        self, fn: Callable[[T], Awaitable["Result[U, E]"]]
    ) -> "Result[U, E]":
        if isinstance(self, Ok):
            return await fn(self.value)
        return self  # type: ignore[return-value]

    # --- Unwraps ---

    @overload
    def unwrap_or(self, default: T) -> T: ...
    @overload
    def unwrap_or(self, default: Callable[[], T]) -> T: ...

    def unwrap_or(self, default: Union[T, Callable[[], T]]) -> T:
        if isinstance(self, Ok):
            return self.value
        return default() if callable(default) else default

    def expect(self, message: str) -> T:
        if isinstance(self, Ok):
            return self.value
        raise RuntimeError(f"{message}: {self.error!r}")

    def unwrap(self) -> T:
        if isinstance(self, Ok):
            return self.value
        raise RuntimeError(f"called unwrap() on Err: {self.error!r}")

    def unwrap_err(self) -> E:
        if isinstance(self, Err):
            return self.error
        raise RuntimeError(f"called unwrap_err() on Ok: {self.value!r}")  # type: ignore[attr-defined]

    def or_else(self, fn: Callable[[E], "Result[T, F]"]) -> "Result[T, F]":
        if isinstance(self, Err):
            return fn(self.error)
        return self  # type: ignore[return-value]

    # --- Matching helpers ---

    def fold(self, on_ok: Callable[[T], U], on_err: Callable[[E], U]) -> U:
        if isinstance(self, Ok):
            return on_ok(self.value)
        return on_err(self.error)  # type: ignore[attr-defined]


@dataclass(slots=True)
class Ok(Result[T, E]):
    value: T


@dataclass(slots=True)
class Err(Result[T, E]):
    error: E
