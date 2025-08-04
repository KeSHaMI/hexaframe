from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class HexaError(Exception):
    """
    Base error for Hexaframe.
    Carries a stable `code`, human-readable `message`,
    and optional serializable `details`.
    """

    code: str
    message: str
    details: Optional[Mapping[str, Any]] = field(default=None)

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = f"{self.code}: {self.message}"
        if self.details:
            return f"{base} details={dict(self.details)}"
        return base


# Domain errors ---------------------------------------------------------------


@dataclass
class DomainError(HexaError):
    """
    Base class for domain-level errors (business rules, invariants).
    """


@dataclass
class ValidationError(DomainError):
    def __init__(
        self, message: str, details: Optional[Mapping[str, Any]] = None
    ) -> None:
        super().__init__(code="validation_error", message=message, details=details)


@dataclass
class NotFound(DomainError):
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(code="not_found", message=message, details=details)


@dataclass
class Conflict(DomainError):
    def __init__(
        self, message: str = "Conflict", details: Optional[Mapping[str, Any]] = None
    ) -> None:
        super().__init__(code="conflict", message=message, details=details)


# Infrastructure / application errors ----------------------------------------


@dataclass
class InfraError(HexaError):
    """
    Errors originating from infrastructure concerns (db, network, io, serialization).
    """


@dataclass
class PermissionDenied(DomainError):
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(code="permission_denied", message=message, details=details)
