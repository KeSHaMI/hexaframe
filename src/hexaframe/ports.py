from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Port(Protocol):
    """
    Marker protocol for Hexaframe ports (dependencies).
    Ports define behavior (contracts) that application/use cases depend on.
    """


@runtime_checkable
class LoggerPort(Port, Protocol):
    """
    Minimal structured logger port. Accepts a message and optional contextual fields.
    """

    def debug(self, msg: str, **fields: Any) -> None: ...
    def info(self, msg: str, **fields: Any) -> None: ...
    def warning(self, msg: str, **fields: Any) -> None: ...
    def error(self, msg: str, **fields: Any) -> None: ...


@runtime_checkable
class ClockPort(Port, Protocol):
    """
    Clock abstraction to enable deterministic tests.
    """

    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


@runtime_checkable
class UuidPort(Port, Protocol):
    """
    UUID provider abstraction. Useful for stubbing in tests.
    """

    def uuid4(self) -> uuid.UUID: ...
    def from_str(self, value: str) -> uuid.UUID: ...
