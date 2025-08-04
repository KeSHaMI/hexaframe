from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class UnitOfWork(Protocol):
    """
    Transaction boundary abstraction.
    Implementations may be sync or async; both context-manager styles are supported.
    """

    # Explicit control
    def begin(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...

    # Optional context manager support (sync)
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc, tb) -> Optional[bool]: ...

    # Optional context manager support (async)
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> Optional[bool]: ...
